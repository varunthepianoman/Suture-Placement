import numpy as np
import cv2
import time
import scipy.interpolate as inter
# from vision.ZividUtils import ZividUtils as ZU
import multiprocessing as mp
import itertools
# from SurgicalSuturing.path import root

from math import factorial

cnt = 0

class InsertionPointGenerator:
    def __init__(self, cut_width=.0075, desired_compute_time=3., space_between_sutures=-1., num_insertion_points=-1):
        assert (num_insertion_points > 0) ^ (
                    space_between_sutures > 0), "specify space_between_sutures OR num_insertion_points"
        self.cut_width = cut_width
        self.space_between_sutures = space_between_sutures
        self.num_insertion_points = num_insertion_points
        self.calculate_num_insertion_points = space_between_sutures > 0

        # self.ZU = ZU('inclined')
        self.which_camera = 'inclined'
        self.which_arm = 'PSM1'
        # self.Trc1 = np.load(
        #     root + f'SurgicalSuturing/calibration_files/Trc_{self.which_camera}_{self.which_arm}.npy')  # robot to camera
        # self.Tcr1 = np.linalg.inv(self.Trc1)

        # W can run optimization for any amount of time. More time is better results.
        # Setting to tiny number (<<1) is undefined behavior.
        self.desired_compute_time = desired_compute_time

        # needed to set above value. printed after any run.
        # self.iters_per_second = 90000 # MacBook Pro (15-inch, 2018)
        self.iters_per_second = 75000  # dvrk

        self.use_multiprocessing = False  # super super buggy on dvrk, not sure why

    def __on_mouse_event(self, event, x, y, flags, param):
        print('click registered')
        blue, red, green = (255, 0, 0), (0, 0, 255), (0, 255, 0)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.is_dragging = True
            self.px = x
            self.py = y
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.is_dragging:
                self.px = x
                self.py = y
        elif event == cv2.EVENT_LBUTTONUP:
            if self.is_dragging:
                self.pnts.append([self.px, self.py])
                self.px, self.py = -1, -1
                self.is_dragging = False
        else:
            return
        print('l59')
        img_draw = self.img_color.copy()
        cv2.circle(img_draw, (self.px, self.py), 3, green, -1)
        for i, pnt in enumerate(self.pnts):
            cv2.circle(img_draw, (pnt[0], pnt[1]), 3, green, -1)
            # cv2.putText(img_draw, str(i), (pnt[0]+10, pnt[1]+10), cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow("IPG Visualizer", img_draw)

    def __user_select_pnts(self):
        # user specify points on the image
        self.pnts = []
        self.is_dragging = False
        self.px, self.py = -1, -1
        # print('self.pnts before imshow', self.pnts)
        print('before create window')
        cv2.imshow("IPG Visualizer", self.img_color)
        # print('self.pnts before mousecallback', self.pnts)
        cv2.setMouseCallback('IPG Visualizer', self.__on_mouse_event)  # fills pnts array
        print('before waitkey')
        cv2.waitKey(0)
        print('after waitkey')
        print('after create window')
        # print('self.pnts before waitkey', self.pnts)
        # cv2.waitKey(0)
        # print('self.pnts before destory', self.pnts)
        # print('self.pnts after destroy', self.pnts)

    def __get_curve(self, pnts):
        ord_dict = {ord(str(i)): i for i in [1, 3, 5, 7]}
        pnts = np.array(pnts)
        key = ord('3')
        while True:
            print('key', key)
            draw_on_img = np.copy(self.img_color)
            if key not in ord_dict:
                print("Invalid Key. Insert 1-9.")
            else:
                deg = ord_dict[key]

            # make spline
            spline = inter.make_interp_spline(x=pnts[:, 1][::-1], y=pnts[:, 0][::-1], k=deg,
                                              bc_type="clamped" if deg == 3 else None)
            start, stop = min(pnts[:, 1]), max(pnts[:, 1])

            # get number of insertion points
            if self.calculate_num_insertion_points:
                waypoints = np.array(self.__find_3d(pnts, self.img_point))  # averages z value of 5 nearest depth points
                print(f'waypoints {waypoints}')
                dist_between = np.linalg.norm(waypoints[1:] - waypoints[:-1], axis=1)
                print(f'waypoints[1:] - waypoints[:-1] {waypoints[1:] - waypoints[:-1]}')
                print(f'dist_between {dist_between}')
                curve_length = np.sum(dist_between)
                self.num_insertion_points = int(np.round(curve_length / self.space_between_sutures, 0))
                print(
                    f"curve_length: {curve_length}, space_between_sutures: {self.space_between_sutures}, num_insertion_points:{self.num_insertion_points}")

            # Based on run time, select, number of points.
            #  n choose k = desired_iters. k is preset, determine n.
            # brute force it since n is small.
            desired_iters = self.desired_compute_time * self.iters_per_second

            num_iters = lambda n, k: factorial(n) / (factorial(k) * factorial(n - k))
            k = self.num_insertion_points
            n = self.num_insertion_points
            print(f'110 n {n} k {k}')
            # n is highest number points we can sample while staying near desired time.
            while num_iters(n, k) < desired_iters:
                print(f'~113 n {n} k {k}')
                n += 1

            while num_iters(n, k) / desired_iters > 1.20:
                print(f'117 n {n} k {k}')
                n -= 1

            self.num_optimization_points = n

            # Can't extract orientation from ends of curve, will be cut off before optimization.
            n += 2
            print(f'124 n {n} k {k}')
            step = abs(stop - start) / float(n)

            y_vals = np.arange(start=start, stop=stop, step=step)
            x_vals = np.array([spline(y) for y in y_vals])
            draw_points = (np.asarray([x_vals, y_vals]).T).astype(np.int32)  # needs to be int32 and transposed
            draw_on_img = cv2.polylines(draw_on_img, [draw_points], False,
                                        (255, 255, 0))  # args: image, points, closed, color
            self.draw_points = draw_points
            for point in draw_points:
                draw_on_img = cv2.circle(draw_on_img, (point[0], point[1]), 4, (0, 150, 0), -1)
            cv2.imshow("IPG Visualizer", draw_on_img)
            key = cv2.waitKey(0)
            if key == 13:
                break
        return np.array(list(zip(x_vals, y_vals)))

    def _update_min_inds(self, inds):
        # exit early if inds not realistic
        if False and (self.use_multiprocessing and inds[0] > 1 or inds[-1] < self.num_optimization_points - 1):
            print(f'self.num_optimization_points {self.num_optimization_points}')
            print('early exit')
            return -1, None

        inds = np.array(inds)
        ins = self.insertion_points[inds]
        s = self.center_of_sutures[inds]
        ext = self.extraction_points[inds]
        # print(f'ins {ins}')
        dist_between_ins = np.linalg.norm(ins[1:] - ins[:-1], axis=1)
        dist_between_s = np.linalg.norm(s[1:] - s[:-1], axis=1)
        dist_between_ext = np.linalg.norm(ext[1:] - ext[:-1], axis=1)

        closest_ins = min(dist_between_ins)
        closest_s = min(dist_between_s)
        closest_ext = min(dist_between_ext)

        furtherest_ins = max(dist_between_ins)
        furtherest_s = max(dist_between_s)
        furtherest_ext = max(dist_between_ext)

        max_dist = furtherest_s + (furtherest_ins / 2) + (furtherest_ext / 2)
        min_dist = closest_s + (closest_ins / 2) + (closest_ext / 2)

        dist_score = min_dist - max_dist
        # print(f'dist_score {dist_score}\n min_dist {min_dist}\n max_dist {max_dist}\n\n')
        # self.__draw_sutures(self.insertion_points, self.orientations, self.center_of_sutures, self.extraction_points)
        return dist_score, inds

    def __get_insertion_points(self, pnts):
        # print(f'~pnts {pnts}')
        # from get_insertion_points_from_selection: pnts is step-spaced points along spline from __get_curve, num pnts [or, stepsize] is based on desired runtime
        orientations = []
        orientation_est_width = 1  # do not change
        for i in range(orientation_est_width, len(pnts)):
            pnt1, pnt2 = pnts[i - orientation_est_width][:2], pnts[i][:2]
            dx, dy = pnt2[0] - pnt1[0], pnt2[1] - pnt1[1]
            normal = np.array([dy, -dx]) / np.linalg.norm([dy, -dx])
            orientations.append(normal)

        orientations = np.array(orientations)

        self.center_of_sutures = pnts[orientation_est_width:]
        self.insertion_points = pnts[orientation_est_width:] + ((orientations * 50) / 2.)
        self.extraction_points = pnts[orientation_est_width:] - ((orientations * 50) / 2.)
        self.orientations = orientations

        num_iters = sum(1 for _ in itertools.combinations(range(len(self.insertion_points)), self.num_insertion_points))

        start = time.time()
        if self.use_multiprocessing:
            with mp.Pool(processes=4) as p:
                results = p.map(self._update_min_inds,
                                itertools.combinations(range(len(self.insertion_points)), self.num_insertion_points))
                results = np.array(results)
        else:
            # all combos of choosing self.num_insertion_points points from list of self.insertion_points_rob
            self.num_insertion_points = min(len(self.insertion_points), self.num_insertion_points)
            # print(f'self.insertion_points_rob\n{self.insertion_points_rob} \nlen of self.insertion_points_rob\n{len(self.insertion_points_rob)} \nself.num_insertion_points {self.num_insertion_points}')
            combos = np.array(
                list(itertools.combinations(range(len(self.insertion_points)), self.num_insertion_points)))
            print(f'~combos\n {combos}')
            # easy speed up: skip all the combos that don't start with 0,1,2,3
            # print(f'self.num_insertion_points: {self.num_insertion_points}\ncombos:\n{combos}')
            # first_invalid_ind = np.argmax(combos[:,0] > 1)
            # print(f'first invalidg ind {first_invalid_ind}')
            # combos = combos[:first_invalid_ind]
            # print(f'combos after \n{combos}')
            # self._update_min_inds returns the diff btw min dist btw insertion pts, and max dist btw insertion pts
            # calculated min/max dist btw insertion pts calculated by averaging min/max center, ins, extr dists,
            # weighting center more
            results = map(self._update_min_inds, combos)
            results = np.array(list(results))

        min_inds = results[np.argmax(results[:, 0])][1]
        time_to_compute = time.time() - start

        print(
            f'n = {len(self.insertion_points)}, k = {self.num_insertion_points}, time = {np.round(time_to_compute, 2)}, iters/sec = {np.round(num_iters / time_to_compute, 2)}, min inds = {min_inds}')
        print('DONE')
        # insertion_points_2d, insertion_points_3d_rob, orientations_rob
        # todo convert the 2d points to 3d_rob points
        return self.insertion_points[min_inds], self.center_of_sutures[min_inds], self.extraction_points[min_inds], \
               self.orientations[min_inds]

    # find 3D points from image points
    def __remove_nan(self, img_point):
        img_point = np.reshape(img_point, (-1, 3))
        img_point = img_point[~np.isnan(img_point).any(axis=1)]
        return img_point

    def __find_3d(self, img_pnts, img_point):
        pnts_3D = []
        for (x, y) in img_pnts:
            x, y = round(int(x)), round(int(y))
            pnt_3D = img_point[y - 5:y + 5, x - 5:x + 5, :]
            pnt_3D = self.__remove_nan(pnt_3D)
            if len(pnt_3D) > 0:
                pnts_3D.append(np.average(pnt_3D, axis=0))
        return np.array(pnts_3D) * 0.001  # (m)

    def __draw_sutures(self, insertion_points, orientations, center_points=None, extraction_points=None,
                       break_out=True):
        draw_on_img = np.copy(self.img_color)
        Tcr1 = np.linalg.inv(self.Trc1)
        if extraction_points is not None and center_points is not None:
            for i, c, e, o in zip(insertion_points, center_points, extraction_points, orientations):
                i_tuple = (int(i[0]), int(i[1]))
                c_tuple = (int(c[0]), int(c[1]))
                e_tuple = (int(e[0]), int(e[1]))
                print(f'i {i}')
                print(f'c {c}')
                print(f'e {e}')
                draw_on_img = cv2.line(draw_on_img, i_tuple, e_tuple, (0, 255, 0), 2)
                draw_on_img = cv2.circle(draw_on_img, i_tuple, 4, (0, 0, 255), -1)
                draw_on_img = cv2.circle(draw_on_img, e_tuple, 4, (255, 0, 0), -1)
        '''
        else:
            for point, orientation in zip(insertion_points, orientations):
                point_tuple = (int(point[0]), int(point[1]))
                d_point_tuple = (int(point[0] + 30), int(point[1]))
                print(f'orientation {orientation}')
                orientation_tuple = (int(point[0] + 50 * orientation[0]), int(point[1] + 50 * orientation[1]))
                draw_on_img = cv2.arrowedLine(draw_on_img, point_tuple, orientation_tuple, color=(0,255,0), thickness=2)
                #draw_on_img = cv2.circle(draw_on_img, point_tuple, 4, (0,255,0), -1)
            for point in self.draw_points:
                draw_on_img = cv2.circle(draw_on_img, (point[0], point[1]), 4, (255, 255, 255), -1)
        '''
        cv2.imshow("IPG Visualizer", draw_on_img)
        cv2.waitKey(0)

    def get_insertion_points_from_selection(self, img_color, img_point):
        self.img_color = img_color
        self.img_point = img_point
        np.save("./record/img_color_inclined.npy", self.img_color)
        np.save("./record/img_point_inclined.npy", self.img_point)

        self.__user_select_pnts()  # fills self.pnts with user selected points
        # print('self.pnts after __user_select_pnts')

        return self.pnts # VARUN: right now we just need the pnts to return, then we will
        curve_pnts = self.__get_curve(
            self.pnts)  # only step-spaced points along spline, display curve # pnts is the [i think pixel coords?] user clicked points [guessing they're supposed to click along the insertion points?]
        # optimized to have min max dist btw points [integrating inserstion, center, extr dists]
        # print('GOT OUT OF __get_curve! curve_pnts: ', curve_pnts)
        ip, cp, ep, o = self.__get_insertion_points(curve_pnts)
        # visualize in gui
        self.__draw_sutures(ip, o, cp, ep, break_out=False)
        return ip, o  # todo fix this to be the right 3d points


if __name__ == "__main__":
    # num_insertion_points = 10
    # IGP = InsertionPointGenerator(desired_compute_time, num_insertion_points=num_insertion_points)
    space_between_sutures = 0.010  # 1 cm
    desired_compute_time = 1
    IGP = InsertionPointGenerator(cut_width=.0075, desired_compute_time=desired_compute_time,
                                  space_between_sutures=space_between_sutures)

    img_color = np.load("record/img_color_inclined.npy")
    img_point = np.load("record/img_point_inclined.npy")
    IGP.get_insertion_points_from_selection(img_color, img_point)
