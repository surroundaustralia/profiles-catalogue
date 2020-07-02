import logging
from xml.dom.minidom import Document as xml_Document
from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
from profcat import config


def version():
    return config.VERSION


def sparql_query(q, sparql_endpoint=config.SPARQL_ENDPOINT, sparql_username=None, sparql_password=None):
    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setQuery(q)
    sparql.setReturnFormat(JSON)

    if sparql_username and sparql_password:
        sparql.setHTTPAuth(BASIC)
        sparql.setCredentials(sparql_username, sparql_password)
    elif config.SPARQL_USERNAME and config.SPARQL_USERNAME:
        sparql.setHTTPAuth(BASIC)
        sparql.setCredentials(config.SPARQL_USERNAME, config.SPARQL_USERNAME)

    try:
        r = sparql.queryAndConvert()

        if isinstance(r, xml_Document):
            def getText(node):
                nodelist = node.childNodes
                result = []
                for node in nodelist:
                    if node.nodeType == node.TEXT_NODE:
                        result.append(node.data)
                return ''.join(result)

            results = []
            for result in r.getElementsByTagName('result'):
                bindings = {}
                for binding in result.getElementsByTagName('binding'):
                    for val in binding.childNodes:
                        bindings[binding.getAttribute("name")] = {
                            "type": "uri" if val.tagName == "uri" else "literal",
                            "value": getText(val)
                        }
                results.append(bindings)
            return results
        elif isinstance(r, dict):
            # JSON
            return r["results"]["bindings"]
        else:
            raise Exception("Could not convert results from SPARQL endpoint")
    except Exception as e:
        logging.debug("SPARQL query failed: {}".format(e))
        logging.debug(
            "endpoint={}\nsparql_username={}\nsparql_password={}\n{}".format(
               q,  sparql_endpoint, sparql_username, sparql_password
            )
        )
        return None
