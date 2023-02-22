import math
import matplotlib.pyplot as plt
import torch as torch
import numpy as np

class DistanceCalculator():

    def __init__(self, wound_width):
        self.wound_width = wound_width
        self.gradients = {}
        pass

    def calculate_distances(self, wound_points):
        # wound points is the set of time-steps along the wound that correspond to wound points

        # Step 1: Calculate insertion and extraction points. Use the wound's
        # evaluate_hodograph function (see bezier_tutorial.py:34) to calculate the tangent/
        # normal, and then wound_width to see where these points are in terms of each wound_point

        # Step 2: Between each adjacent pair of wound_points, with i
        # as wound point index, must calculate dist(i, i + 1) for
        # insert, center extract: refer to slide 13 for details:

        # gets the norm of the vector (1, gradient)
        num_pts = len(wound_points)

        def get_norm(gradient):
            return math.sqrt(1 + gradient**2)

        # might be worth vecotrizing in the future
            
        # get the curve and gradient for each point (the second argument allows you to on the fly take the derivative)
        wound_curve = self.wound(wound_points, 0)
        wound_derivatives = self.wound(wound_points, 1)
        wound_curve_torch = torch.tensor(wound_curve, requires_grad=True)
        wound_derivatives_torch = torch.tensor(wound_derivatives, requires_grad=True)
        wound_points_torch = torch.tensor(wound_points, requires_grad=True)

        # extract the norms of the vectors
        norms = [get_norm(wound_derivative) for wound_derivative in wound_derivatives]

        # get the normal vectors as norm = 1
        normal_vecs = [[wound_derivatives[i]/norms[i], -1/norms[i]] for i in range(num_pts)]
        
        # make norm width wound_width
        normal_vecs = [[normal_vec[0] * self.wound_width, normal_vec[1] * self.wound_width] for normal_vec in normal_vecs]

        # add and subtract for insertion and exit
        insert_pts = [[wound_points[i] + normal_vecs[i][0], wound_curve[i] + normal_vecs[i][1]] for i in range(num_pts)]

        extract_pts = [[wound_points[i] - normal_vecs[i][0], wound_curve[i] - normal_vecs[i][1]] for i in range(num_pts)]

        center_pts = [[wound_points[i], wound_curve[i]] for i in range(num_pts)]

        # verify works by plotting
        #plt.scatter([insert_pts[i][0] for i in range(num_pts)], [insert_pts[i][1] for i in range(num_pts)], c="red")
        #plt.scatter([extract_pts[i][0] for i in range(num_pts)], [extract_pts[i][1] for i in range(num_pts)], c="blue")
        #plt.scatter([center_pts[i][0] for i in range(num_pts)], [center_pts[i][1] for i in range(num_pts)], c="green")

        def euclidean_distance(point1, point2):
            x1, y1, x2, y2 = point1[0], point1[1], point2[0], point2[1]
            return math.sqrt((x2-x1)**2+(y2-y1)**2)

        def dist_insert(i):
            return euclidean_distance(insert_pts[i], insert_pts[i+1])

        def dist_center(i):
            return euclidean_distance(center_pts[i], center_pts[i+1])

        def dist_extract(i):
            return euclidean_distance(extract_pts[i], extract_pts[i+1])

        
        #for all i:
            # calculate insert, center, extract distances
        # return 3 lists: insert dists, center dists, extract dists

        
        insert_distances = []
        center_distances = []
        extract_distances = []
        
        center_grads = np.zeros((len(wound_points) - 1, len(wound_points)))

        for i in range(num_pts - 1):
            insert_distances.append(dist_insert(i))
            center_distances.append(dist_center(i))
            extract_distances.append(dist_extract(i))
            dc = torch.sqrt(torch.square(wound_points_torch[i+1] - wound_points_torch[i]) + torch.square(wound_curve_torch[i+1] - wound_curve_torch[i]))
            dc.backward()
            center_grads[i][:] = (wound_points_torch.grad + torch.mul(wound_curve_torch.grad, wound_derivatives_torch)).cpu().detach().numpy()
            wound_points_torch.grad.zero_()
            wound_curve_torch.grad.zero_()

        self.gradients['center'] = center_grads.T
        self.gradients['insert'] = 0
        self.gradients['extract'] = 0


        # print('insert distances\n', insert_distances, '\ncenter_distances\n', center_distances, '\nextract_distances\n', extract_distances)
        # for i, txt in enumerate(insert_distances):
        #     print('type text', type(txt))
        #     plt.annotate("{:.4f}".format(txt), (insert_pts[i][0], insert_pts[i][1]))
        # for i, txt in enumerate(center_distances):
        #     print('type text', type(txt))
        #     plt.annotate("{:.4f}".format(txt), (center_pts[i][0], center_pts[i][1]))
        # for i, txt in enumerate(extract_distances):
        #     print('type text', type(txt))
        #     plt.annotate("{:.4f}".format(txt), (extract_pts[i][0], extract_pts[i][1]))

        # plt.show()

        return insert_distances, center_distances, extract_distances
    
    def grads(self, wound_points):
        return self.gradients
    
    def plot(self, wound_points):
        num_pts = len(wound_points)

        def get_norm(gradient):
            return math.sqrt(1 + gradient**2)

        # might be worth vecotrizing in the future
            
        # get the curve and gradient for each point (the second argument allows you to on the fly take the derivative)
        wound_curve = self.wound(wound_points, 0)
        wound_derivatives = self.wound(wound_points, 1)

        # extract the norms of the vectors
        norms = [get_norm(wound_derivative) for wound_derivative in wound_derivatives]

        # get the normal vectors as norm = 1
        normal_vecs = [[wound_derivatives[i]/norms[i], -1/norms[i]] for i in range(num_pts)]
        
        # make norm width wound_width
        normal_vecs = [[normal_vec[0] * self.wound_width, normal_vec[1] * self.wound_width] for normal_vec in normal_vecs]

        # add and subtract for insertion and exit
        insert_pts = [[wound_points[i] + normal_vecs[i][0], wound_curve[i] + normal_vecs[i][1]] for i in range(num_pts)]

        extract_pts = [[wound_points[i] - normal_vecs[i][0], wound_curve[i] - normal_vecs[i][1]] for i in range(num_pts)]

        center_pts = [[wound_points[i], wound_curve[i]] for i in range(num_pts)]

        # verify works by plotting
        plt.scatter([insert_pts[i][0] for i in range(num_pts)], [insert_pts[i][1] for i in range(num_pts)], c="red")
        plt.scatter([extract_pts[i][0] for i in range(num_pts)], [extract_pts[i][1] for i in range(num_pts)], c="blue")
        plt.scatter([center_pts[i][0] for i in range(num_pts)], [center_pts[i][1] for i in range(num_pts)], c="green")
        plt.show()



"""
x = initial_x
rv = [0, 0, 0] #c, e, i
y = f(x)
y = torch.tensor(y, requires_grad=True)
g = torch.tensor(f'(x), requires_grad=True)
dc = h(y)
dc.backwards()
rv[0] = y.grad * f'(x)
temp = q(g) # temp = 2wsin(theta)
temp.backwards()
rv[1] = rv[0] + g.grad * f''(x)
rv[2] = rv[0] - g.grad * f''(x)
return rv
#d(dists)/dx
"""