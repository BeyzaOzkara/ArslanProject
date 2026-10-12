import json
import os
from functools import wraps
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Avg, Max, Min
from django.views.decorators.csrf import csrf_exempt

from django.apps import apps
from django.db import DEFAULT_DB_ALIAS

# Basic Token Authentication for the AI Agent
AGENT_API_KEY = os.environ.get('AGENT_API_KEY', '123api')

def require_agent_token(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Allow checking either the Header or the query parameter
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif 'token' in request.GET:
            token = request.GET['token']
            
        if token != AGENT_API_KEY:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Allowed models and their corresponding databases
# Every registered model is allowed. Models can be referenced either by class name
# (e.g. 'KalipMs') or by 'app_label.ClassName' (e.g. 'DMS.Document') to avoid clashes.
DIES_MODELS = {
    'KalipMs', 'ProfilMs', 'PresUretimRaporu', 'SiparisList', 'MusteriFirma',
    'TestereDepo', 'BilletDepoTransfer', 'HammaddePartiListesi', 'UretimBasilanBillet', 'UretimPartiAnaliz'
}
DMS_MODELS = {'EventData', 'IO_List', 'Recipe'}

def _db_for_model(m):
    if m.__name__ in DIES_MODELS:
        return 'dies'
    if m.__name__ in DMS_MODELS:
        return 'dms'
    return DEFAULT_DB_ALIAS

def _build_allowed_models():
    allowed = {}
    for m in apps.get_models():
        config = {'model': m, 'db': _db_for_model(m)}
        allowed[f"{m._meta.app_label}.{m.__name__}"] = config
        # Plain class name; first registered model wins on name clashes
        allowed.setdefault(m.__name__, config)
    return allowed

ALLOWED_MODELS = _build_allowed_models()

ALLOWED_LOOKUPS = {
    'exact', 'iexact', 'contains', 'icontains', 
    'gt', 'lt', 'gte', 'lte', 'in', 'startswith', 
    'endswith', 'isnull'
}

ALLOWED_AGGREGATIONS = {
    'Sum': Sum,
    'Count': Count,
    'Avg': Avg,
    'Max': Max,
    'Min': Min,
}

@csrf_exempt
@require_agent_token
def dynamic_ai_query(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    model_name = data.get('model')
    if model_name not in ALLOWED_MODELS:
        return JsonResponse({'error': f'Model {model_name} is not allowed or does not exist.'}, status=400)

    model_config = ALLOWED_MODELS[model_name]
    ModelClass = model_config['model']
    db_name = model_config['db']

    # Initialize the base read-only queryset
    qs = ModelClass.objects.using(db_name).all()

    # Apply AND filters
    filters = data.get('filters', [])
    filter_kwargs = {}
    for f in filters:
        field = f.get('field')
        lookup = f.get('lookup', 'exact')
        value = f.get('value')
        
        if lookup not in ALLOWED_LOOKUPS:
            return JsonResponse({'error': f'Invalid lookup: {lookup}'}, status=400)
            
        filter_kwargs[f"{field}__{lookup}"] = value

    if filter_kwargs:
        qs = qs.filter(**filter_kwargs)

    # Apply OR filters
    # Example format: "or_filters": [[{"field": "A", "value": 1}, {"field": "B", "value": 2}]]
    or_filters = data.get('or_filters', [])
    for or_group in or_filters:
        q_object = Q()
        for f in or_group:
            field = f.get('field')
            lookup = f.get('lookup', 'exact')
            value = f.get('value')
            
            if lookup not in ALLOWED_LOOKUPS:
                return JsonResponse({'error': f'Invalid lookup in OR filter: {lookup}'}, status=400)
                
            q_object |= Q(**{f"{field}__{lookup}": value})
        qs = qs.filter(q_object)

    # Apply Exclude filters
    excludes = data.get('exclude', [])
    exclude_kwargs = {}
    for e in excludes:
        field = e.get('field')
        lookup = e.get('lookup', 'exact')
        value = e.get('value')
        
        if lookup not in ALLOWED_LOOKUPS:
            return JsonResponse({'error': f'Invalid lookup in exclude: {lookup}'}, status=400)
            
        exclude_kwargs[f"{field}__{lookup}"] = value

    if exclude_kwargs:
        qs = qs.exclude(**exclude_kwargs)

    # Apply Order By
    order_by = data.get('order_by', [])
    if order_by:
        qs = qs.order_by(*order_by)

    # Values (Fields to return)
    values = data.get('values', [])

    # Aggregations
    aggregations_data = data.get('aggregations', [])
    aggregation_kwargs = {}
    for agg in aggregations_data:
        agg_type = agg.get('type')
        field = agg.get('field')
        alias = agg.get('alias', f"{field}_{agg_type.lower()}")
        
        if agg_type not in ALLOWED_AGGREGATIONS:
            return JsonResponse({'error': f'Invalid aggregation type: {agg_type}'}, status=400)
            
        AggFunction = ALLOWED_AGGREGATIONS[agg_type]
        aggregation_kwargs[alias] = AggFunction(field)

    # Evaluate the Queryset securely
    try:
        # If there are aggregations and no values, it's a global aggregate
        if aggregation_kwargs and not values:
            result = qs.aggregate(**aggregation_kwargs)
            return JsonResponse({'data': result})
            
        # If there are values and aggregations, it's a grouped annotation
        elif aggregation_kwargs and values:
            qs = qs.values(*values).annotate(**aggregation_kwargs)
            return JsonResponse({'data': list(qs)})
            
        # Normal query (just filtering and returning specific fields)
        elif values:
            qs = qs.values(*values)
            return JsonResponse({'data': list(qs)})
            
        # Fallback (return everything as dict) - WARNING: Can be token heavy
        else:
            # We limit to 100 rows by default if no values are provided to prevent massive payloads
            qs = qs.values()[:100]
            return JsonResponse({'data': list(qs), 'warning': 'No values specified. Result limited to 100 rows.'})
            
    except Exception as e:
        return JsonResponse({'error': f'Query execution failed: {str(e)}'}, status=500)


@csrf_exempt
@require_agent_token
def model_list(request):
    """GET: returns a plain list of all allowed model class names."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)
    names = sorted({cfg['model'].__name__ for cfg in ALLOWED_MODELS.values()})
    return JsonResponse({'data': names})


@csrf_exempt
@require_agent_token
def model_schema(request):
    """
    GET: returns every allowed model with its db alias, db table, and fields/types.
    Optional query param ?model=Name (class name or app_label.ClassName) for a single model.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)

    def describe(cfg):
        m = cfg['model']
        fields = []
        for f in m._meta.get_fields():
            if not getattr(f, 'concrete', False):
                continue  # skip reverse relations / non-column fields
            info = {
                'name': f.name,
                'type': f.get_internal_type(),
                'column': f.column,
                'null': f.null,
                'primary_key': f.primary_key,
            }
            if getattr(f, 'max_length', None):
                info['max_length'] = f.max_length
            if f.is_relation and f.related_model is not None:
                info['related_model'] = f.related_model.__name__
            fields.append(info)
        return {
            'model': m.__name__,
            'app_label': m._meta.app_label,
            'db': cfg['db'],
            'db_table': m._meta.db_table,
            'managed': m._meta.managed,
            'fields': fields,
        }

    requested = request.GET.get('model')
    if requested:
        if requested not in ALLOWED_MODELS:
            return JsonResponse({'error': f'Model {requested} is not allowed or does not exist.'}, status=400)
        return JsonResponse({'data': describe(ALLOWED_MODELS[requested])})

    # Plain-name aliases point to the same config, so list each model once
    seen, result = set(), []
    for cfg in ALLOWED_MODELS.values():
        if cfg['model'] in seen:
            continue
        seen.add(cfg['model'])
        result.append(describe(cfg))
    return JsonResponse({'data': result})
