import numpy as np
import sympy
import logging
from typing import Tuple
from shapely.geometry import shape, Polygon
import math
import matplotlib.pyplot as plt
import constants




class Player:
    def __init__(self, skill: int, rng: np.random.Generator, logger: logging.Logger) -> None:
        """Initialise the player with given skill.

        Args:
            skill (int): skill of your player
            rng (np.random.Generator): numpy random number generator, use this for same player behvior across run
            logger (logging.Logger): logger use this like logger.info("message")
        """
        self.skill = skill
        self.rng = rng
        self.logger = logger
        self.centers =[]
        self.centerset ={}
        self.centers2 []
    
    def segmentize_map(self, golf_map ):
        area_length = 5
        beginx = area_length/2
        beginy = area_length/2
        endx = constants.vis_width
        endy = constants.vis_height
        
        node_centers = []
        node_centers2 =[]
        
        for i in range(beginx, endx, area_length):
            tmp = []    
            for j in range(beginy, endy, area_length):
                representative_point = Point(i,j)
                if (golf_map.encloses(representative_point)):
                    tmp.append(representative_point)
                    node_centers.append(representative_point)
                    self.centerset.add((i,j))
                else:
                    tmp.append(None)
            nodes_centers2.append(tmp)

        self.centers = node_centers
        self.centers2 = nodes_centers2
        

        
        



    def sector(self, center, start_angle, end_angle, radius):
        def polar_point(origin_point, angle,  distance):
            return [origin_point.x + math.sin(math.radians(angle)) * distance, origin_point.y + math.cos(math.radians(angle)) * distance]
        steps=50
        if start_angle > end_angle:
            t = start_angle
            start_angle = end_angle
            end_angle = t
        else:
            pass
        step_angle_width = (end_angle-start_angle) / steps
        sector_width = (end_angle-start_angle) 
        segment_vertices = []

        segment_vertices.append(polar_point(center, 0,0))
        segment_vertices.append(polar_point(center, start_angle,radius))
        

        for z in range(1, steps):
            segment_vertices.append((polar_point(center, start_angle + z * step_angle_width,radius)))
        segment_vertices.append(polar_point(center, start_angle+sector_width,radius))
        #print(segment_vertices)
        return Polygon(segment_vertices)

    def positionSafety(self, d, angle, start_point, golf_map):
        #CIRCLE of radiues = 2 standand deviations
        angle_2std = math.degrees(2*(1/self.skill))
        distance_2std = 2*(d/self.skill)
        center = start_point
        print("start ")
        print(angle + angle_2std)
        print("end ")
        print(angle - angle_2std)
        #print("end "+ angle - angle_2std)
        sector1 = self.sector(center, angle + angle_2std, angle - angle_2std, d - distance_2std)
        sector2 = self.sector(center, angle + angle_2std, angle - angle_2std, d + distance_2std )
        probable_landing_region = sector1.intersection(sector2)
        shape_map = golf_map.vertices
        x,y = probable_landing_region.exterior.xy
        shape_map_work = Polygon(shape_map)
        #fig = plt.figure()
        #plt.plot(x,y)
        #plt.show()
        
        area_inside_the_polygon =  (probable_landing_region.intersection(shape_map_work).area)/probable_landing_region.area
        print(area_inside_the_polygon)

    def travel_extra_10percent_safety(self, d, angle, start_point, golf_map):
        angle_2std = math.degrees(2*(1/self.skill))
        distance_2std = 2*(d/self.skill)
        center = start_point
        sector1 = self.sector(center, angle + angle_2std, angle - angle_2std, d + distance_2std + 0.1*d)
        sector2 = self.sector(center, angle + angle_2std, angle - angle_2std, d + distance_2std )
        probable_landing_region = sector1.intersection(sector2)
        shape_map = golf_map.vertices
        x,y = probable_landing_region.exterior.xy
        shape_map_work = Polygon(shape_map)

        

        return (area_inside_the_polygon)

    def find_center(self, mylocation):
        x = mylocation.x
        y = mylocation.y
        bucketx = x // 5
        buckety = y // 5
        mycenterx = 5*bucketx +2.5
        mycentery = 5*buckety +2.5
        center = Point(mycenterx,mycentery)
        if (self.centers2[bucketx][buckety] != None)
            return self.centers2[bucketx][buckety]
        mind =1000000000
        for points in self.centers:
            distance = mylocation.distance(points)
            if (distance < mind):
                mind = distance
                center = points
        return center

    def ( )


    def play(self, score: int, golf_map: sympy.Polygon, target: sympy.geometry.Point2D, curr_loc: sympy.geometry.Point2D, prev_loc: sympy.geometry.Point2D, prev_landing_point: sympy.geometry.Point2D, prev_admissible: bool) -> Tuple[float, float]:
        """Function which based n current game state returns the distance and angle, the shot must be played 

        Args:
            score (int): Your total score including current turn
            golf_map (sympy.Polygon): Golf Map polygon
            target (sympy.geometry.Point2D): Target location
            curr_loc (sympy.geometry.Point2D): Your current location
            prev_loc (sympy.geometry.Point2D): Your previous location. If you haven't played previously then None
            prev_landing_point (sympy.geometry.Point2D): Your previous shot landing location. If you haven't played previously then None
            prev_admissible (bool): Boolean stating if your previous shot was within the polygon limits. If you haven't played previously then None

        Returns:
            Tuple[float, float]: Return a tuple of distance and angle in radians to play the shot
        """
        if (prev_loc == None):
            self.segmentize_map

        center = self.find_center(curr_loc.evalf())
        next_point = self.path_finder(center, target )


        print(curr_loc)
        required_dist = curr_loc.distance(target)
        roll_factor = 1.1
        if required_dist < 20:
            roll_factor  = 1.0
        distance = sympy.Min(200+self.skill, required_dist/roll_factor)
        angle = sympy.atan2(target.y - curr_loc.y, target.x - curr_loc.x)
        angle2  = math.degrees(angle)
        a =  self.positionSafety( distance, angle2, curr_loc.evalf(), golf_map)

        return (distance, angle)
