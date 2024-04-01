import ezdxf
import math
from ezdxf.math import Vec2, bulge_to_arc

def triangle_calculate(base, hyp):
    height = (hyp**2 - (base/2)**2)**0.5
    return base * height / 2

def polyline_area_calculate(points):
    area = 0.0
    perimeter = 0.0
    path = ''
    for i in range(len(points)):
        x0, y0, b0 = points[i][0], points[i][1], points[i][2]
        x1, y1, b1 = points[(i + 1) % len(points)][0], points[(i + 1) % len(points)][1], points[(i + 1) % len(points)][2]

        area += (x0 * y1 - x1 * y0) / 2
        
        if b0 != 0:
            arc = ezdxf.math.bulge_to_arc(Vec2(x0, y0), Vec2(x1, y1), b0)
            center = arc[0]
            start_angle = arc[1]
            end_angle = arc[2]
            radius = arc[3]
            sector_area = abs(0.5 * (abs(end_angle) - abs(start_angle)) * radius ** 2)
            triangle_area = abs(triangle_calculate(((x1-x0)**2 + (y1-y0)**2)**0.5, radius))
            
            if b0 < 0:
                area -= (sector_area - triangle_area)
                sweep_flag = 0
            else:
                area += (sector_area - triangle_area)
                sweep_flag = 1
            perimeter += abs(abs(end_angle) - abs(start_angle)) * radius
            if path != "":
                path = path + f"A{round(radius,2)} {round(radius,2)} 0 0 {sweep_flag} {round(x1,2)} {round(y1,2)} "
            else:
                path = f'<path d="M{round(x0,2)} {round(y0,2)} A{round(radius,2)} {round(radius,2)} 0 0 {sweep_flag} {round(x1,2)} {round(y1,2)}'
        else:
            perimeter += abs((x1 - x0)**2 + (y1 - y0)**2)**0.5
            if path == "":
                path = f'<path d="M{round(x1,2)} {round(y1,2)} '
            else:
                path = path + f"L{round(x1,2)} {round(y1,2)} "
    path = path + 'Z"'
    return [abs(area), perimeter, path]

def dxf_file_area_calculation(file_path):
    areas = []
    perimeters = []
    paths = []
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    for e in msp.query('LWPOLYLINE'):
        if e.closed:
            points = e.get_points('xyb')
            results = polyline_area_calculate(points)
            area, perimeter, path = results[0], results[1], results[2]
            perimeters.append(perimeter)
            areas.append(area)
            paths.append(path)
    for e in msp.query('CIRCLE'):
        area = math.pi * (e.dxf.radius ** 2)
        areas.append(area)
        perimeters.append(math.pi * e.dxf.radius * 2)
        paths.append(f'<circle r="{round(e.dxf.radius,2)}" cx="{round(e.dxf.center[0],2)}" cy="{round(e.dxf.center[1],2)}" ')
    
    return areas, perimeters, paths