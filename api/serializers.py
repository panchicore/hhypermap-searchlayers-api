import re
from . import utils
from rest_framework import serializers



class SearchSerializer(serializers.Serializer):
    q_time = serializers.CharField(
        required=False,
        help_text="Constrains docs by time range. Either side can be '*' to signify open-ended. "
                  "Otherwise it must be in either format as given in the example. UTC time zone is implied. Example: "
                  "[2013-03-01 TO 2013-04-01T00:00:00]"
    )
    q_geo = serializers.CharField(
        required=False,
        help_text="A rectangular geospatial filter in decimal degrees going from the lower-left to the upper-right. "
                  "The coordinates are in lat,lon format. "
                  "Example: [-90,-180 TO 90,180]"
    )
    q_text = serializers.CharField(
        required=False,
        help_text="Constrains docs by keyword search query."
    )
    q_user = serializers.CharField(
        required=False,
        help_text="Constrains docs by matching exactly a certain user."
    )
    d_docs_limit = serializers.IntegerField(
        required=False,
        help_text="How many documents to return.",
        default=0
    )
    d_docs_sort = serializers.ChoiceField(
        required=False,
        help_text="How to order the documents before returning the top X. 'score' is keyword search relevancy. "
                  "'time' is time descending. 'distance' is the distance between the doc and the middle of q.geo.",
        default="score",
        choices=["score", "time", "distance"]
    )
    a_time_limit = serializers.IntegerField(
        required=False,
        help_text="Non-0 triggers time/date range faceting. This value is the maximum number of time ranges to "
                  "return when a.time.gap is unspecified. This is a soft maximum; less will usually be returned. "
                  "A suggested value is 100. Note that a.time.gap effectively ignores this value. "
                  "See Solr docs for more details on the query/response format.",
        default=0
    )
    a_time_gap = serializers.CharField(
        required=False,
        help_text="The consecutive time interval/gap for each time range. Ignores a.time.limit.The format is based on "
                  "a subset of the ISO-8601 duration format."
    )
    a_time_filter = serializers.CharField(
        required=False,
        help_text="From what time range to divide by a.time.gap into intervals. Defaults to q.time and otherwise 90 days."
    )

    a_hm_limit = serializers.IntegerField(
        required=False,
        help_text="Non-0 triggers heatmap/grid faceting. This number is a soft maximum on thenumber of cells it should have. "
                  "There may be as few as 1/4th this number in return. Note that a.hm.gridLevel can effectively ignore "
                  "this value. The response heatmap contains a counts grid that can be null or contain null rows when "
                  "all its values would be 0. See Solr docs for more details on the response format.",
        default=0
    )
    a_hm_gridlevel = serializers.IntegerField(
        required=False,
        help_text="To explicitly specify the grid level, e.g. to let a user ask for greater or courser resolution "
                  "than the most recent request. Ignores a.hm.limit."
    )
    a_hm_filter = serializers.CharField(
        required=False,
        help_text="To explicitly specify the grid level, e.g. to let a user ask for greater or courser resolution "
                  "than the most recent request. Ignores a.hm.limit."
    )

    a_text_limit = serializers.IntegerField(
        required=False,
        help_text="Returns the most frequently occurring words. WARNING: There is usually a significant performance "
                  "hit in this due to the extremely high cardinality.",
        default=0
    )
    a_user_limit = serializers.IntegerField(
        required=False,
        help_text="Returns the most frequently occurring users.",
        default=0
    )
    return_solr_original_response = serializers.IntegerField(
        required=False,
        help_text="Returns te original solr response.",
        default=0
    )




    def validate_q_time(self, value):
        """
        Would be for example: [2013-03-01 TO 2013-04-01T00:00:00] and/or [* TO *]
        Returns a valid sorl value. [2013-03-01T00:00:00Z TO 2013-04-01T00:00:00Z] and/or [* TO *]
        """
        if value:
            try:
                start, end = utils.parse_datetime_range(value)
                left = '*'
                if start:
                    left = start.isoformat() + 'Z'
                right = '*'
                if end:
                    right = end.isoformat() + 'Z'
                return "[{0} TO {1}]".format(left, right)
            except Exception as e:
                raise serializers.ValidationError(e.message)

        return value

    def validate_q_geo(self, value):
        """
        Would be for example: [-90,-180 TO 90,180]
        """
        if value:
            try:
                utils.parse_geo_box(value)
            except Exception as e:
                raise serializers.ValidationError(e.message)

        return value

    def validate_a_time_filter(self, value):
        """
        Would be for example: [2013-03-01 TO 2013-04-01:00:00:00] and/or [* TO *]
        """
        if value:
            try:
                utils.parse_datetime_range(value)
            except Exception as e:
                raise serializers.ValidationError(e.message)

        return value




class Timing(serializers.Serializer):
    label = serializers.CharField()
    millis = serializers.IntegerField()
    subs = serializers.ListField()

class SearchResponse(serializers.Serializer):
    a_matchDocs = serializers.IntegerField(default=0)
    d_docs = serializers.ListField(required=False)
    timing = Timing(required=False)

