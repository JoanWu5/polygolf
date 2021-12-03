import time

import numpy as np
import sympy
import logging
from typing import Tuple
import constants
from numba import jit


def get_distance(point1, point2):
    return pow(point1.x - point2.x, 2) + pow(point1.y - point2.y, 2)


@jit(nopython=True)
def point_inside_polygon(poly: np.array, px: float, py: float) -> bool:
    # http://paulbourke.net/geometry/polygonmesh/#insidepoly
    # https://stackoverflow.com/questions/36399381/whats-the-fastest-way-of-checking-if-a-point-is-inside-a-polygon-in-python
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if min(p1y, p2y) < py <= max(p1y, p2y) and px <= max(p1x, p2x) and p1x != p2y:
            xints = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or px <= xints:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)


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
        # TODO: define the risk rate, which means we can only take risks at 10%
        self.risk = 0.1
        self.simulate_times = 100
        self.tolerant_times = self.simulate_times * self.risk
        self.remember_middle_points = []

        self.turn = 0
        self.golf_map_np = None

    def play(self, score: int, golf_map: sympy.Polygon, target: sympy.geometry.Point2D,
             curr_loc: sympy.geometry.Point2D, prev_loc: sympy.geometry.Point2D,
             prev_landing_point: sympy.geometry.Point2D, prev_admissible: bool) -> Tuple[float, float]:
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
        if self.turn == 0:
            self.golf_map_np = np.asarray([(float(p.x), float(p.y)) for p in golf_map.vertices])

        self.turn += 1
        # 1. always try greedy first
        required_dist = curr_loc.distance(target)
        roll_factor = 1. + constants.extra_roll
        if required_dist < constants.min_putter_dist:
            roll_factor = 1.0
        distance = sympy.Min(constants.max_dist + self.skill, required_dist / roll_factor)
        angle = sympy.atan2(target.y - curr_loc.y, target.x - curr_loc.x)

        is_greedy = True
        failed_times = 0
        # simulate the actual situation to ensure fail times will not be larger than self.tolerant_times
        for _ in range(self.simulate_times):
            is_succ, final_point = self.simulate_once(distance, angle, curr_loc, golf_map)
            if not is_succ:
                failed_times += 1
                if failed_times > self.tolerant_times:
                    is_greedy = False
                    break

        if is_greedy:
            self.logger.info(str(self.turn) + "select greedy strategy to go")
            return (distance, angle)

        # 2. if we cannot use greedy, we try to find the points intersected with the golf map
        if prev_admissible is None or prev_admissible or not self.remember_middle_points:
            circle = sympy.Circle(curr_loc, distance)
            # TODO: cost about 6-8 seconds, too slow
            intersect_points_origin = circle.intersection(golf_map)

            intersect_points_num = len(intersect_points_origin)
            temp_middle_points = []

            for i in range(intersect_points_num):
                for j in range(i + 1, intersect_points_num):
                    middle_point = sympy.Point2D(float(intersect_points_origin[i].x + intersect_points_origin[j].x) / 2,
                                                 float(intersect_points_origin[i].y + intersect_points_origin[j].y) / 2)
                    # find points that in the golf map polygon
                    if golf_map.encloses(middle_point):
                        temp_middle_points.append(middle_point)

            if len(temp_middle_points) == 0:
                self.logger.error(str(self.turn) + "cannot find any middle point, BUG!!!")
                return (distance, angle)

            # if there are many ways to go, delete the points that can go back
            middle_points = []
            for i, middle_point in enumerate(temp_middle_points):
                if middle_point.distance(target) > required_dist:
                    continue
                middle_points.append(middle_point)

            # if there we delete every point in temp_middle_points,
            # which means we could go longer ways than expected, we need to add back those points
            if len(middle_points) == 0:
                middle_points = temp_middle_points

            self.remember_middle_points = middle_points
        else:
            middle_points = list(self.remember_middle_points)

        middle_points_num = len(middle_points)
        mid_to_target_distance = [0] * middle_points_num
        for i, middle_point in enumerate(middle_points):
            mid_to_target_distance[i] = middle_point.distance(target)

        distance_sorted_indexes = sorted(range(middle_points_num), key=lambda x: mid_to_target_distance[x])

        middle_failed_times = [0] * middle_points_num

        midd_index = -1
        for i in distance_sorted_indexes:
            middle_point = middle_points[i]
            angle = sympy.atan2(middle_point.y - curr_loc.y, middle_point.x - curr_loc.x)
            for _ in range(self.simulate_times):
                is_succ, final_point = self.simulate_once(distance, angle, curr_loc, golf_map)
                if not is_succ:
                    middle_failed_times[i] += 1
                    if middle_failed_times[i] > self.tolerant_times:
                        middle_failed_times[i] = -1
                        break

            if middle_failed_times[i] != -1:
                midd_index = i
                break

        desire_distance = distance
        if midd_index != -1:
            self.logger.info(str(self.turn) + "select largest distance to middle point to go")
            desire_angle = sympy.atan2(middle_points[midd_index].y - curr_loc.y,
                                       middle_points[midd_index].x - curr_loc.x)

            return (desire_distance, desire_angle)

        # 3. if middle points are still not safe, choose the closest one to the target
        closest_index = distance_sorted_indexes[0]
        closest_middle_point = middle_points[closest_index]

        curr_to_mid = closest_middle_point.distance(curr_loc)
        desire_distance = sympy.Min(constants.max_dist + self.skill, curr_to_mid / roll_factor)
        desire_angle = sympy.atan2(closest_middle_point.y - curr_loc.y, closest_middle_point.x - curr_loc.x)
        self.logger.info(str(self.turn) + "risky!!! select closest middle point to go")
        return (desire_distance, desire_angle)

    def simulate_once(self, distance, angle, curr_loc, golf_map):
        actual_distance = self.rng.normal(distance, distance / self.skill)
        actual_angle = self.rng.normal(angle, 1 / (2 * self.skill))

        # landing_point means the land point(the golf can skip for a little distance),
        # final_point means the final stopped point, it is not equal
        if distance < constants.min_putter_dist:
            landing_point = curr_loc
            final_point = Point(curr_loc.x + actual_distance * np.cos(actual_angle),
                                curr_loc.y + actual_distance * np.sin(actual_angle))

        else:
            landing_point = Point(curr_loc.x + actual_distance * np.cos(actual_angle),
                                  curr_loc.y + actual_distance * np.sin(actual_angle))
            final_point = Point(
                curr_loc.x + (1. + constants.extra_roll) * actual_distance * np.cos(actual_angle),
                curr_loc.y + (1. + constants.extra_roll) * actual_distance * np.sin(actual_angle))

        is_inside = point_inside_polygon(golf_map, landing_point.x, landing_point.y) and \
                    point_inside_polygon(golf_map, final_point.x, final_point.y)

        return is_inside, final_point

    def get_points_inside_circle(self, points_score, curr_loc, radius, target):
        circle_points = dict()
        max_dist = radius ** 2

        for points in points_score.keys():
            if get_distance(curr_loc, points) <= max_dist:
                circle_points[points] = points_score[points]

        sorted_points_score = dict(sorted(circle_points.items(), key=lambda x: x[1]))
        smallest_score = min(sorted_points_score.values())
        smallest_score_points = dict()
        for points, value in sorted_points_score.items():
            if value == smallest_score:
                smallest_score_points[points] = get_distance(target, points)

        closest2target_points = dict(sorted(smallest_score_points.items(), key=lambda x:x[1]))
        safe_point = None
        unsafe_points2score = dict()
        for point in closest2target_points.keys():
            succ_times = 0
            for _ in range(self.simulate_times):
                angle = sympy.atan2(point.y - curr_loc.y, point.x - curr_loc.x)
                is_succ, _ = self.simulate_once(get_distance(curr_loc, point), angle, curr_loc, self.golf_map_np)
                succ_times += is_succ

            if succ_times / self.simulate_times >= 1 - self.risk:
                safe_point = point
                break

            unsafe_points2score[point] = succ_times

        if safe_point is None:
            unsafe_points = sorted(unsafe_points2score.items(), key=lambda x: -x[1])
            safe_point = unsafe_points[0][0]

        desire_distance = get_distance(curr_loc, safe_point)
        desire_angle = sympy.atan2(safe_point.y - curr_loc.y, safe_point.x - curr_loc.x)
        return (desire_distance, desire_angle)

