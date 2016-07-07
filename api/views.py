import requests
from rest_framework.views import APIView
from rest_framework.response import Response

from api.utils import parse_geo_box, request_time_facet, request_field_facet
from serializers import SearchSerializer, SearchResponse, Timing

# - OPEN API specs
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/1.2.md#parameterObject

TIME_FILTER_FIELD = "layer_date"
GEO_FILTER_FIELD = "bbox"
USER_FIELD = "layer_originator"
TEXT_FIELD = "title"
TIME_SORT_FIELD = "layer_date"
GEO_SORT_FIELD = "bbox"

class Search(APIView):

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
          defaultValue: "[1900-01-01 TO 2016-01-01T00:00:00]"
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

        - name: a_text_limit
          description: "Returns the most frequently occurring words. WARNING: There is usually a significant performance hit in this due to the extremely high cardinality."
          in: query
          required: false
          type: integer
          paramType: query
          defaultValue: "0"
        - name: a_user_limit
          description: Returns the most frequently occurring users.
          in: query
          required: false
          type: integer
          paramType: query
          defaultValue: "0"
        - name: return_solr_original_response
          description: Just for debugging purposes when 1 will return the original solr response.
          in: query
          required: false
          type: integer
          paramType: query
          defaultValue: "0"

        responseMessages:
          - code: 200
            message: Search completed.
          - code: 400
            message: Validation errors.
        """

        serializer = SearchSerializer(data=request.GET)
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
            a_text_limit = serializer.validated_data.get("a_text_limit")
            a_user_limit = serializer.validated_data.get("a_user_limit")
            return_solr_original_response = serializer.validated_data.get("return_solr_original_response")

            print serializer.validated_data

            # query params to be sent via restful solr
            params = {
                "q": "*:*",
                "indent": "on",
                "wt": "json",
                "rows": d_docs_limit,
                "facet": "off",
                "facet.field": [],
                "debug": "timing"
            }
            if q_text:
                params["q"] = q_text

            # query params for filters
            filters = []
            if q_time:
                # TODO: when user sends incomplete dates like 2000, its completed: 2000-(TODAY-MONTH)-(TODAY-DAY)T00:00:00Z
                # TODO: "Invalid Date in Date Math String:'[* TO 2000-12-05T00:00:00Z]'"
                # Kotlin like: "{!field f=layer_date tag=layer_date}[* TO 2000-12-05T00:00:00Z]"
                # then do it simple:
                filters.append("{0}:{1}".format(TIME_FILTER_FIELD, q_time))
            if q_geo:
                filters.append("{0}:{1}".format(GEO_FILTER_FIELD, q_geo))
            if q_user:
                filters.append("{{!field f={0} tag={0}}}{1}".format(USER_FIELD, q_user))
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

            if a_text_limit > 0:
                params["facet"] = 'on'
                params["facet.field"].append(TEXT_FIELD)
                params["f.{}.facet.limit".format(TEXT_FIELD)] = a_text_limit

            if a_user_limit > 0:
                params["facet"] = 'on'
                params["facet.field"].append("{{! ex={0}}}{0}".format(USER_FIELD))
                params["f.{}.facet.limit".format(USER_FIELD)] = a_user_limit

            # solr request
            collection = "hypermap2"
            solr_url = "http://54.221.223.91:8983/solr/{}/select".format(collection)

            res = requests.get(
                solr_url, params=params
            )

            solr_response = res.json()
            solr_response["solr_request"] = res.url

            if return_solr_original_response > 0:
                return Response(solr_response)

            # create the response dict following the swagger model:
            data = {}
            response = solr_response["response"]
            data["a.matchDocs"] = response.get("numFound")

            if response.get("docs"):
                data["d.docs"] = response.get("docs")

            if a_time_limit > 0:
                date_facet = solr_response["facet_counts"]["facet_ranges"][TIME_FILTER_FIELD]
                a_time = {
                    "start": date_facet.get("start"),
                    "end": date_facet.get("end"),
                    "gap": date_facet.get("gap"),
                    "counts": date_facet.get("counts")
                }
                data["a.time"] = a_time

            data["a.hm"] = "#TODO"

            if a_user_limit > 0:
                user_facet = solr_response["facet_counts"]["facet_fields"][USER_FIELD]
                data["a.user"] = user_facet

            if a_text_limit > 0:
                text_facet = solr_response["facet_counts"]["facet_fields"][TEXT_FIELD]
                data["a.text"] = text_facet

            subs = []
            for label, values in solr_response["debug"]["timing"].iteritems():
                if type(values) is not dict:
                    continue
                subs_data = {"label": label, "subs": []}
                for label, values in values.iteritems():
                    if type(values) is not dict:
                        subs_data["millis"] = values
                        continue
                    subs_data["subs"].append({
                        "label": label,
                        "millis": values.get("time")
                    })
                subs.append(subs_data)

            timing = {
                "label": "requests.get.elapsed",
                "millis": res.elapsed,
                "subs": [{
                    "label": "QTime",
                    "millis": solr_response["responseHeader"].get("QTime"),
                    "subs": subs
                }]
            }

            data["timing"] = timing

            return Response(data)
