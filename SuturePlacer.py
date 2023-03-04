import DistanceCalculator
import RewardFunction
import Optimizer
import scipy.optimize as optim

class SuturePlacer:
    def __init__(self):
        # This object should contain the optimizer, the spline curve, the image, etc., i.e. all of the relevant objects involved, as attributes.
        self.wound_width = 0.3 # TODO Varun: this is a random #, lookup
        self.DistanceCalculator = DistanceCalculator.DistanceCalculator(self.wound_width)
        self.RewardFunction = RewardFunction.RewardFunction()

        # NB: Viraj: added a class in order to allow code to run
        self.Optimizer = Optimizer.Optimizer() # cvxpy? Feel free to make your own file with a class for Optimizer if you want one.

    def place_sutures(self):
        # I want it to have an initial placement and then a forward pass thru to the reward so we can test our code.
        # Maybe this initial placement could be based on some smart heuristic to make optimization faster...
       
        # choosing 11 equally spaced points along curve as placeholder
        wound_points = [0.0, 0.05, 0.25, 0.45, 0.65, 0.75, 0.85, 0.9] # TODO Harshika/Viraj: Initial Placement, can put some placeholder here
        self.DistanceCalculator.plot(wound_points)
        # print("Initial wound points", wound_points)
        start = wound_points[0]
        end = wound_points[-1]
        
        def final_loss(t):
            self.RewardFunction.insert_dists, self.RewardFunction.center_dists, self.RewardFunction.extract_dists, insert_pts, center_pts, extract_pts = self.DistanceCalculator.calculate_distances(t)    
            return self.RewardFunction.lossX()
        
        def con2(t):
            insert_dists, center_dists, extract_dists, insert_pts, center_pts, extract_pts = self.DistanceCalculator.calculate_distances(t)   
            h = 0.3
            return [i - h for i in insert_dists] + [i - h for i in center_dists] + [i - h for i in extract_dists]

        print(final_loss(wound_points))
        con = ({'type': 'eq', 'fun': lambda t: t[0] - start}, {'type': 'eq', 'fun': lambda t: t[-1] - end}, 
               {'type': 'ineq', 'fun': con2}
               )
        result = optim.minimize(final_loss, wound_points, constraints = con)
        print(self.DistanceCalculator.calculate_distances(result.x))
        print(final_loss(result.x))
        self.DistanceCalculator.plot(result.x)
        return result.x
        




        # Then, we can use the initial placement to warm-start the optimization process.
        # self.Optimizer.optimize_placement(grads1, grads2) # TODO Viraj/Yashish: the variables to optimize
        # [TODO] are the wound_points. These are parametric values for locations on the wound.
        #  [TODO] Wound should already be passed in by main.py:place_sutures.