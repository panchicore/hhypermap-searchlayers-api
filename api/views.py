import requests
from rest_framework.views import APIView
from rest_framework.response import Response

from api.utils import parse_geo_box, request_time_facet
from serializers import TweetsSearchSerializer

# - OPEN API specs
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/1.2.md#parameterObject

TIME_FILTER_FIELD = "created_at"
GEO_FILTER_FIELD = "coord_rpt"
USER_FIELD = "user_name"
TEXT_FIELD = "text"
TIME_SORT_FIELD = "id"
GEO_SORT_FIELD = "coord"

class TweetsSearch(APIView):

    def get(self, request):
        """
        The q. parameters qre query/constraints that limit the matching documents.
        The d. params control returning the documents. The a. params are faceting/aggregations on a field of the documents.
        The .limit params limit how many top values/docs to return. Some of the formatting and response structure
        has strong similarities with Apache Solr, unsurprisingly.
        ---
        parameters:
        - name: q_time
          description: Constrains docs by time range. Either side can be '*' to signify open-ended. Otherwise it must be in either format as given in the example. UTC time zone is implied.
          in: query
          required: false
          type: string
          paramType: query
          defaultValue: "[2013-03-01 TO 2013-04-01T00:00:00]"
        - name: q_geo
          description: A rectangular geospatial filter in decimal degrees going from the lower-left to the upper-right. The coordinates are in lat,lon format.
          in: query
          required: false
          type: string
          paramType: query
          defaultValue: "[-90,-180 TO 90,180]"
        - name: q_text
          in: query
          description: Constrains docs by keyword search query.
          required: false
          type: string
          paramType: query
        - name: q_user
          in: query
          description: Constrains docs by matching exactly a certain user
          required: false
          type: string
          paramType: query
        - name: d_docs_limit
          description: How many documents to return.
          in: query
          required: false
          type: integer
          paramType: query
          defaultValue: "0"
        - name: d_docs_sort
          description: How to order the documents before returning the top X. 'score' is keyword search relevancy. 'time' is time descending. 'distance' is the distance between the doc and the middle of q.geo.
          in: query
          required: false
          type: integer
          paramType: query
          defaultValue: "score"
          enum: [ "score", "time", "distance" ]
        - name: a_time_limit
          description: Non-0 triggers time/date range faceting. This value is the maximum number of time ranges to return when a.time.gap is unspecified. This is a soft maximum; less will usually be returned. A suggested value is 100. Note that a.time.gap effectively ignores this value. See Solr docs for more details on the query/response format.
          in: query
          required: false
          type: integer
          paramType: query
          defaultValue: "0"
        - name: a_time_gap
          description: The consecutive time interval/gap for each time range. Ignores a.time.limit.The format is based on a subset of the ISO-8601 duration format.
          in: query
          required: false
          type: string
          paramType: query
          defaultValue: "P1D"
        - name: a_time_filter
          description: From what time range to divide by a.time.gap into intervals. Defaults to q.time and otherwise 90 days.
          in: query
          required: false
          type: string
          paramType: query

        responseMessages:
          - code: 200
            message: Search completed.
          - code: 400
            message: Validation errors.
        """

        print request.GET

        serializer = TweetsSearchSerializer(data=request.GET)
        if serializer.is_valid(raise_exception=True):

            q_time = serializer.validated_data.get("q_time")
            q_geo = serializer.validated_data.get("q_geo")
            q_text = serializer.validated_data.get("q_text")
            q_user = serializer.validated_data.get("q_user")
            d_docs_limit = serializer.validated_data.get("d_docs_limit")
            d_docs_sort = serializer.validated_data.get("d_docs_sort")
            a_time_limit = serializer.validated_data.get("a_time_limit")
            a_time_gap = serializer.validated_data.get("a_time_gap")
            a_time_filter = serializer.validated_data.get("a_time_filter")

            print serializer.validated_data

            # query params to be sent via restful solr
            params = {
                "q": "*:*",
                "indent": "on",
                "wt": "json",
                "rows": d_docs_limit
            }
            if q_text:
                params["q"] = q_text

            # query params for filters
            filters = []
            if q_time:
                filters.append("{0}:{1}".format(TIME_FILTER_FIELD, q_time))
            if q_geo:
                filters.append("{0}:{1}".format(GEO_FILTER_FIELD, q_geo))
            if q_user:
                filters.append("{!field f=%s tag=%s}%s" % (USER_FIELD, USER_FIELD, q_user))
            if filters: params["fq"] = filters

            # query params for ordering
            if d_docs_sort == 'score' and q_text:
                params["sort"] = 'score desc'
            elif d_docs_sort == 'time':
                params["sort"] = '{} desc'.format(TIME_SORT_FIELD)
            elif d_docs_sort == 'distance':
                rectangle = parse_geo_box(q_geo)
                params["sort"] = 'geodist() asc'
                params["sfield"] = GEO_SORT_FIELD
                params["pt"] = '{0},{1}'.format(rectangle.centroid.x, rectangle.centroid.y)

            # query params for facets
            if a_time_limit > 0:
                params["facet"] = 'on'
                time_filter = a_time_filter or q_time or None
                facet_parms = request_time_facet(TIME_FILTER_FIELD, time_filter, a_time_gap, a_time_limit)
                params.update(facet_parms)

            # solr request
            collection = "hypermap2"
            solr_url = "http://54.221.223.91:8983/solr/{}/select".format(collection)

            res = requests.get(
                solr_url, params=params
            )

            solr_response = res.json()
            solr_response["solr_request"] = res.url

            return Response(solr_response)





