"""Classes that are useful to async_tasks and are not database models."""
import bson
from .models import TimeSeriesData

class PathNotFoundException(Exception):
    pass

class TimeSeriesQuery(object):
    """Represents a user query against time series data."""
    def __init__(self, user, parent_path, match = None, group_by = None,
    aggregate = None, min_date = None, max_date = None, sort = None,
    continuous = False, model_class = TimeSeriesData):
        self.user = user
        self.parent_path = parent_path
        self.match = match
        self.group_by = list(set(group_by) & set(model_class.dimensions))
        self.aggregate = aggregate if not aggregate else {
            k: v for k, v in aggregate.items() if k in model_class.dimensions}
        self.min_date = min_date
        self.max_date = max_date
        self.sort = sort
        self.continuous = continuous
        self.model_class = model_class
    
    def totals(self):
        """Returns summed totals."""
        pre_grouping_id = {}
        aggregation = self.begin_aggregation([self.parent_path])
        
        for dimension in self.group_by:
            if dimension != "value":
                pre_grouping_id[dimension] = '$'+dimension
        
        aggregation.append({"$group":
            {"value":{"$sum":"$value"}, "_id": pre_grouping_id }})
        pre_projection = dict([(dimension, '$_id.'+dimension
            ) for dimension in self.group_by])
        pre_projection['value'] = '$value'
        aggregation.append({"$project": pre_projection})
        
        aggregation += self.finish_aggregation()
        
        return self.model_class.get_collection(
            ).aggregate(aggregation).get('result')
        
    def averages(self):
        """Returns summed totals divided by the parent path's summed totals."""
        aggregation = self.begin_aggregation([
            "/".join(self.parent_path[0:-1].split("/")[0:-1])+"/",
            self.parent_path])
        
        grouping_id = self.get_grouping_id()
        
        # subgrouping_id is also used for projecting the fields in the previous
        # query's _id field back to the top level.
        subgrouping_id = {dimension: '$_id.'+dimension
            for dimension in grouping_id}
             
        # Sum totals by parent path.
        aggregation.append({"$group": {"_id": dict(
                grouping_id.items() + [
                    ("parent_path", "$parent_path"), ("user_id", "$user_id")]),
            "value":{"$sum":"$value"}}})
            
        # Collect total sums according to user_id.
        # There should be at most two user_ids in our pipeline at this point:
        # the current user's user_id and (if we're getting a "continuous"
        # stream) a null user_id. By using "max" and "min," we are able to split
        # up the sums from the two paths we're concerned with and pass them on
        # to the next grouping operator.
        aggregation.append({"$group": {
            "_id": dict(subgrouping_id.items() + [("user_id", "$_id.user_id")]),
             "numerator": {"$min": "$value"},
             "denominator": {"$max": "$value"}}})
             
        if self.continuous:
            # Collapsing the null user and current user paths to *actually*
            # group by the fields in the group_by list and fill the gaps in the
            # data series with zeroes.
            aggregation.append({"$group": {
                "_id": dict(subgrouping_id.items()),
                 "numerator": {"$sum": "$numerator"},
                 "denominator": {"$sum": "$denominator"}}})
            
        # Calculate out the averages, removing the _id entry and including the
        # groupBy entries as we do so. We're also using $divide to calculate our
        # average out here, and protecting it from division by zero with $cond.
        aggregation.append({"$project": 
            dict([("value", {"$cond": [{"$eq":["$denominator", 0]}, 0,
                                {"$divide": ["$numerator", "$denominator"]}]}),
                  ("_id", 0)] + subgrouping_id.items()
            )})
        
        aggregation += self.finish_aggregation()
        
        return self.model_class.get_collection(
            ).aggregate(aggregation).get('result')
        
    def begin_aggregation(self, parent_paths):
        """Sets up initial filtering based on min_date, max_date, and user_id"""
        aggregation = []
        parent_path_query = [{"parent_path": path} for path in parent_paths]
        
        if self.continuous:
            user_id_query = {
                "$or": [{"user_id": self.user['_id']}, {"user_id":None}]}
            name_query = {"$or": [{"name": "total.json"}, {"name": None}]}
            parent_path_query.append({'parent_path': None})
        else:
            user_id_query = {"user_id": self.user['_id']}
            name_query = {"name": "total.json"}
        
        match = [user_id_query, {"$or": parent_path_query}, name_query]
        
        if self.min_date:
            match.append({"timestamp": {"$gte": self.min_date}})
            
        if self.max_date:
            match.append({"timestamp": {"$lt": self.max_date}})
            
        aggregation.append({"$match": {"$and": match}})
        
        return aggregation
        
    def finish_aggregation(self):
        """Tack on the requested filters after we've done our transforms."""
        aggregation = []
        
        if self.match:
            aggregation.append({'$match': self.match})
        
        if self.aggregate:
            grouping = {dimension: {'$'+aggregator: '$'+dimension}
                for dimension, aggregator in self.aggregate.items()}
                    
            if self.group_by:
                grouping['_id'] = {dimension: '$'+dimension
                    for dimension in self.group_by}
            else:
                grouping['_id'] = self.get_grouping_id()
                
            # Flatten the results and remove all internal-use fields.
            post_projection = {dimension: 1
                for dimension in self.aggregate.keys()}
            post_projection.update({dimension: '$_id.' + dimension
                for dimension in self.group_by})
            post_projection['_id'] = 0 
            
            aggregation.append({'$group': grouping})
            aggregation.append({"$project": post_projection})
        
        if self.sort:
            aggregation.append({'$sort': bson.SON(self.sort)})
            
        return aggregation
        
    def get_grouping_id(self):
        """Returns the _id parameters for our grouping functions."""
        
        # Grab the dimensions the user wants to work with.
        dimensions = []
        if self.aggregate:
            dimensions += self.aggregate.keys()
        
        if self.group_by:
            dimensions += self.group_by
            
        if not self.aggregate and not self.group_by:
            dimensions = self.model_class.default_group_by
            
        return {dimension: '$'+dimension for dimension in dimensions}


class UserTimeSeriesQuery(TimeSeriesQuery):
    def __init__(self, user, path, **kwargs):
        path_parts = path.split("/")
        parent_path = "/".join(path_parts[0:-1]) + "/"
        self.aspect_name = path_parts[-1]
        super(UserTimeSeriesQuery, self).__init__(user, parent_path, **kwargs)
    
    def get_data(self):
        if self.aspect_name == "totals":
            return self.totals()
        elif self.aspect_name == "averages":
            return self.averages()
        else:
            raise PathNotFoundException(
                "Path not recognized: %s" % self.aspect_name)
            
