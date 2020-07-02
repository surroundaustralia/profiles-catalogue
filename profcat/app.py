import sys

sys.path.insert(0, '../../')
sys.path.insert(0, '../vocprez/')

import logging
from profcat import config

import io
from rdflib import Graph
from flask import (
    Flask,
    Response,
    request,
    render_template,
    g,
    redirect,
    url_for,
)

app = Flask(
    __name__, template_folder=config.TEMPLATES_DIR, static_folder=config.STATIC_DIR
)


# @app.context_processor
# def context_processor():
#     """
#     A set of variables available globally for all Jinja templates.
#     :return: A dictionary of variables
#     :rtype: dict
#     """
#
#     MEDIATYPE_NAMES = {
#         "text/html": "HTML",
#         "application/json": "JSON",
#         "text/turtle": "Turtle",
#         "application/rdf+xml": "RDX/XML",
#         "application/ld+json": "JSON-LD",
#         "text/n3": "Notation-3",
#         "application/n-triples": "N-Triples",
#     }
#
#     import profcat.u.utils as u
#     return dict(
#         utils=u
#     )


@app.route("/")
def index():
    return render_template(
        "index.html",
    )


@app.route("/about")
def about():
    # import os
    #
    # # using basic Markdown method from http://flask.pocoo.org/snippets/19/
    # with open(os.path.join(config.APP_DIR, "..", "README.md")) as f:
    #     content = f.read()
    #
    # # make images come from wed dir
    # content = content.replace(
    #     "vocprez/view/style/", request.url_root + "style/"
    # )
    # content = Markup(markdown.markdown(content))

    return render_template(
        "about.html"
        #content=content
    )


@app.route("/profile/")
def profiles():
    return render_template(
        "profiles.html",
    )

    # page = (
    #     int(request.values.get("page")) if request.values.get("page") is not None else 1
    # )
    # per_page = (
    #     int(request.values.get("per_page"))
    #     if request.values.get("per_page") is not None
    #     else 20
    # )
    # #
    # # # TODO: replace this logic with the following
    # # #   1. read all static vocabs from g.VOCABS
    # # get this instance's list of vocabs
    # vocabs = []  # local copy (to this request) for sorting
    # for k, voc in g.VOCABS.items():
    #     vocabs.append((url_for("object", uri=k), voc.title))
    # vocabs.sort(key=lambda tup: tup[1])
    # total = len(g.VOCABS.items())
    # #
    # # # Search
    # # query = request.values.get("search")
    # # results = []
    # # if query:
    # #     for m in match(vocabs, query):
    # #         results.append(m)
    # #     vocabs[:] = results
    # #     vocabs.sort(key=lambda v: v.title)
    # #     total = len(vocabs)
    # #
    # # # generate vocabs list for requested page and per_page
    # start = (page - 1) * per_page
    # end = start + per_page
    # vocabs = vocabs[start:end]
    #
    # return ContainerRenderer(
    #     request,
    #     config.VOCS_URI if config.VOCS_URI is not None else url_for("vocabularies"),
    #     config.VOCS_TITLE if config.VOCS_TITLE is not None else 'Vocabularies',
    #     config.VOCS_DESC if config.VOCS_DESC is not None else None,
    #     None,
    #     None,
    #     vocabs,
    #     total
    # ).render()


@app.route("/object")
def object():
    """
    This is the general RESTful endpoint and corresponding Python function to handle requests for individual objects,
    be they a Vocabulary, Concept Scheme, Collection or Concept. Only those 4 classes of object are supported for the
    moment.

    An HTTP URI query string argument parameter 'vocab_uri' may be supplied, indicating the vocab this object is within
    An HTTP URI query string argument parameter 'uri' must be supplied, indicating the URI of the object being requested

    :return: A Flask Response object
    :rtype: :class:`flask.Response`
    """

    uri = request.values.get("uri")
    vocab_uri = request.values.get("vocab_uri")

    uri_is_empty = True if uri is None or uri == "" else False
    vocab_uri_is_empty = True if vocab_uri is None or vocab_uri == "" else False

    # must have a URI or Vocab URI supplied, for any scenario
    if uri_is_empty and vocab_uri_is_empty:
        return error_response(
            "Input Error",
            400,
            "A Query String Argument of 'uri' and/or 'vocab_uri' must be supplied for this endpoint"
        )
    elif uri_is_empty and not vocab_uri_is_empty:
        # we only have a vocab_uri, so it must be a vocab
        v = return_vocab(vocab_uri)
        if v is not None:
            return v
        # if we haven't returned already, the vocab_uri was unknown but that's all we have so error
        return error_response(
            "vocab_uri error",
            400,
            markdown.markdown(
                "You have supplied an unknown 'vocab_uri'. If one is supplied, "
                "it must be one of:\n\n"
                "{}".format("".join(["* " + str(x) + "   \n" for x in g.VOCABS.keys()]))
            ),
        )
    elif not uri_is_empty and vocab_uri_is_empty:
        # we have no vocab_uri so we must be able to return a result from the main cache or error
        # if it's a vocab, return that
        v = return_vocab(uri)
        if v is not None:
            return v
        # if we get here, it's not a vocab so try to return a Collection or Concept from the main cache
        c = return_collection_or_concept_from_main_cache(uri)
        if c is not None:
            return c
        # if we get here, it's neither a vocab nor a Concept of Collection so return error
        return error_response(
            "Input Error",
            400,
            "The 'uri' you supplied is not known to this instance of VocPrez. You may consider supplying a 'vocab_uri' "
            "parameter with that same 'uri' to see if VocPrez can use that vocab URI to look up information about "
            "the 'uri' object' from a remote source."
        )
    else:  # both uri & vocab_uri are set
        # look up URI at vocab_uri source. If not found, return error

        # we have a vocab_uri, so it must be a real one
        if vocab_uri not in g.VOCABS.keys():
            return error_response(
                "Input Error",
                400,
                markdown.markdown(
                    "You have supplied an unknown 'vocab_uri'. If one is supplied, "
                    "it must be one of:\n\n"
                    "{}".format("".join(["* " + str(x) + "   \n" for x in g.VOCABS.keys()]))
                ),
            )

        # the vocab_uri is valid so query that vocab's source for the object
        # the uri is either a Concept or Collection.
        c = return_collection_or_concept_from_vocab_source(vocab_uri, uri)
        if c is not None:
            return c

        # if we get here, neither a Collection nor a Concept could be found at that vocab's source so error
        return error_response(
            "Input Error",
            400,
            "You supplied a valid 'vocab_uri' but when VocPrez queried the relevant vocab, no information about the "
            "object you identified with 'uri' was found.",
        )


# the SPARQL UI
@app.route("/sparql", methods=["GET", "POST"])
def sparql():
    return render_template(
        "sparql.html",
    )


# the SPARQL endpoint under-the-hood
@app.route("/endpoint", methods=["GET", "POST"])
def endpoint():
    """
    TESTS

    Form POST:
    curl -X POST -d query="PREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0ASELECT%20*%20WHERE%20%7B%3Fs%20a%20skos%3AConceptScheme%20.%7D" http://localhost:5000/endpoint

    Raw POST:
    curl -X POST -H 'Content-Type: application/sparql-query' --data-binary @query.sparql http://localhost:5000/endpoint
    using query.sparql:
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT * WHERE {?s a skos:ConceptScheme .}

    GET:
    curl http://localhost:5000/endpoint?query=PREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0ASELECT%20*%20WHERE%20%7B%3Fs%20a%20skos%3AConceptScheme%20.%7D

    GET CONSTRUCT:
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        CONSTRUCT {?s a rdf:Resource}
        WHERE {?s a skos:ConceptScheme}
    curl -H 'Accept: application/ld+json' http://localhost:5000/endpoint?query=PREFIX%20rdf%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F1999%2F02%2F22-rdf-syntax-ns%23%3E%0APREFIX%20skos%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fco23%3E%0ACONSTRUCT%20%7B%3Fs%20a%20rdf%3AResource%7D%0AWHERE%20%7B%3Fs%20a%20skos%3AConceptScheme%7D

    """
    logging.debug("request: {}".format(request.__dict__))

    # TODO: Find a slightly less hacky way of getting the format_mimetime value
    format_mimetype = request.__dict__["environ"]["HTTP_ACCEPT"]

    # Query submitted
    if request.method == "POST":
        """Pass on the SPARQL query to the underlying endpoint defined in config
        """
        if "application/x-www-form-urlencoded" in request.content_type:
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-urlencoded

            2.1.2 query via POST with URL-encoded parameters

            Protocol clients may send protocol requests via the HTTP POST method by URL encoding the parameters. When
            using this method, clients must URL percent encode all parameters and include them as parameters within the
            request body via the application/x-www-form-urlencoded media type with the name given above. Parameters must
            be separated with the ampersand (&) character. Clients may include the parameters in any order. The content
            type header of the HTTP request must be set to application/x-www-form-urlencoded.
            """
            if (
                    request.values.get("query") is None
                    or len(request.values.get("query")) < 5
            ):
                return Response(
                    "Your POST request to the SPARQL endpoint must contain a 'query' parameter if form posting "
                    "is used.",
                    status=400,
                    mimetype="text/plain",
                )
            else:
                query = request.values.get("query")
        elif "application/sparql-query" in request.content_type:
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-direct

            2.1.3 query via POST directly

            Protocol clients may send protocol requests via the HTTP POST method by including the query directly and
            unencoded as the HTTP request message body. When using this approach, clients must include the SPARQL query
            string, unencoded, and nothing else as the message body of the request. Clients must set the content type
            header of the HTTP request to application/sparql-query. Clients may include the optional default-graph-uri
            and named-graph-uri parameters as HTTP query string parameters in the request URI. Note that UTF-8 is the
            only valid charset here.
            """
            query = request.data.decode("utf-8")  # get the raw request
            if query is None:
                return Response(
                    "Your POST request to this SPARQL endpoint must contain the query in plain text in the "
                    "POST body if the Content-Type 'application/sparql-query' is used.",
                    status=400,
                )
        else:
            return Response(
                "Your POST request to this SPARQL endpoint must either the 'application/x-www-form-urlencoded' or"
                "'application/sparql-query' ContentType.",
                status=400,
            )

        try:
            if "CONSTRUCT" in query:
                format_mimetype = "text/turtle"
                return Response(
                    sparql_query2(
                        query, format_mimetype=format_mimetype
                    ),
                    status=200,
                    mimetype=format_mimetype,
                )
            else:
                return Response(
                    sparql_query2(query, format_mimetype),
                    status=200,
                )
        except ValueError as e:
            return Response(
                "Input error for query {}.\n\nError message: {}".format(query, str(e)),
                status=400,
                mimetype="text/plain",
            )
        except ConnectionError as e:
            return Response(str(e), status=500)
    else:  # GET
        if request.args.get("query") is not None:
            # SPARQL GET request
            """
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-get

            2.1.1 query via GET

            Protocol clients may send protocol requests via the HTTP GET method. When using the GET method, clients must
            URL percent encode all parameters and include them as query parameter strings with the names given above.

            HTTP query string parameters must be separated with the ampersand (&) character. Clients may include the
            query string parameters in any order.

            The HTTP request MUST NOT include a message body.
            """
            query = request.args.get("query")
            if "CONSTRUCT" in query:
                acceptable_mimes = [x for x in Renderer.RDF_MEDIA_TYPES]
                best = request.accept_mimetypes.best_match(acceptable_mimes)
                query_result = sparql_query2(
                    query, format_mimetype=best
                )
                file_ext = {
                    "text/turtle": "ttl",
                    "application/rdf+xml": "rdf",
                    "application/ld+json": "json",
                    "text/n3": "n3",
                    "application/n-triples": "nt",
                }
                return Response(
                    query_result,
                    status=200,
                    mimetype=best,
                    headers={
                        "Content-Disposition": "attachment; filename=query_result.{}".format(
                            file_ext[best]
                        )
                    },
                )
            else:
                query_result = sparql_query2(query)
                return Response(
                    query_result, status=200, mimetype="application/sparql-results+json"
                )
        else:
            # SPARQL Service Description
            """
            https://www.w3.org/TR/sparql11-service-description/#accessing

            SPARQL services made available via the SPARQL Protocol should return a service description document at the
            service endpoint when dereferenced using the HTTP GET operation without any query parameter strings
            provided. This service description must be made available in an RDF serialization, may be embedded in
            (X)HTML by way of RDFa, and should use content negotiation if available in other RDF representations.
            """

            acceptable_mimes = [x for x in Renderer.RDF_MEDIA_TYPES] + ["text/html"]
            best = request.accept_mimetypes.best_match(acceptable_mimes)
            if best == "text/html":
                # show the SPARQL query form
                return redirect(url_for("sparql"))
            elif best is not None:
                for item in Renderer.RDF_MEDIA_TYPES:
                    if item == best:
                        rdf_format = best
                        return Response(
                            get_sparql_service_description(
                                rdf_format=rdf_format
                            ),
                            status=200,
                            mimetype=best,
                        )

                return Response(
                    "Accept header must be one of " + ", ".join(acceptable_mimes) + ".",
                    status=400,
                )
            else:
                return Response(
                    "Accept header must be one of " + ", ".join(acceptable_mimes) + ".",
                    status=400,
                )


def get_sparql_service_description(rdf_format="turtle"):
    """Return an RDF description of PROMS' read only SPARQL endpoint in a requested format

    :param rdf_format: 'turtle', 'n3', 'xml', 'json-ld'
    :return: string of RDF in the requested format
    """
    sd_ttl = """
        @prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sd:     <http://www.w3.org/ns/sparql-service-description#> .
        @prefix sdf:    <http://www.w3.org/ns/formats/> .
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <http://gnafld.net/sparql>
            a                       sd:Service ;
            sd:endpoint             <%(BASE_URI)s/function/sparql> ;
            sd:supportedLanguage    sd:SPARQL11Query ; # yes, read only, sorry!
            sd:resultFormat         sdf:SPARQL_Results_JSON ;  # yes, we only deliver JSON results, sorry!
            sd:feature sd:DereferencesURIs ;
            sd:defaultDataset [
                a sd:Dataset ;
                sd:defaultGraph [
                    a sd:Graph ;
                    void:triples "100"^^xsd:integer
                ]
            ]
        .
    """
    g = Graph().parse(io.StringIO(sd_ttl), format="turtle")
    rdf_formats = list(set([x for x in Renderer.RDF_SERIALIZER_TYPES_MAP]))
    if rdf_format[0][1] in rdf_formats:
        return g.serialize(format=rdf_format[0][1])
    else:
        raise ValueError(
            "Input parameter rdf_format must be one of: " + ", ".join(rdf_formats)
        )


def sparql_query2(query, format_mimetype="application/json"):
    """ Make a SPARQL query"""
    logging.debug("sparql_query2: {}".format(query))
    data = query

    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": format_mimetype,
        "Accept-Encoding": "UTF-8",
    }
    if hasattr(config, "SPARQL_USERNAME") and hasattr(config, "SPARQL_PASSWORD"):
        auth = (config.SPARQL_USERNAME, config.SPARQL_PASSWORD)
    else:
        auth = None

    try:
        logging.debug(
            "endpoint={}\ndata={}\nheaders={}".format(
                config.SPARQL_ENDPOINT, data, headers
            )
        )
        r = requests.post(
            config.SPARQL_ENDPOINT, auth=auth, data=data, headers=headers, timeout=60
        )
        logging.debug("response: {}".format(r.__dict__))
        return r.content.decode("utf-8")
    except Exception as e:
        raise e


# TODO: use for all errors
# TODO: allow conneg - at least text v. HTML
def error_response(title, status, message):
    return render_template(
        "error.html",
        title=title,
        status=status,
        msg=message
    ), status


# run the Flask app
if __name__ == "__main__":
    logging.basicConfig(
        filename=config.LOGFILE,
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s",
    )

    import os

    sources_folder = os.path.join(config.APP_DIR, "source")
    main_module = "__init__"
    import importlib


    def ge_sources():
        plugins = []
        possible_sources = os.listdir(sources_folder)
        for i in possible_sources:
            location = os.path.join(sources_folder, i)
            info = importlib.find_module(main_module, [location])
            plugins.append({"name": i, "info": info})
        return plugins


    def load_plugin(plugin):
        return importlib.load_module(main_module, *plugin["info"])


    app.run(debug=config.DEBUG, threaded=True, port=5000)