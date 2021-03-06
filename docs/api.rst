.. _api:

Developer Interface
===================

This part of the documentation is related to the REST API used to interact with this backend.
The examples in this part of the documentation use :

   * IP as 127.0.0.1
   * a resource name as service

Browse Alignak backend API (Swagger)
------------------------------------

The Alignak backend API can be browsed with a Web Browser on this URL::

    http://127.0.0.1:5000/docs

This URL is served by the Swagger UI embedded into the Alignak backend.


Authentication in the backend
-----------------------------

The backend API needs an authentication for each request. Some user accounts are defined with *username*, *password* and *token*.

To access any backend enpoint, you need to provide the *token* associated to the user account.

Get the authentication token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

POST on *http://127.0.0.1:5000/login* with fields:

* *username*: xxx
* *password*: xxx

Example 1, JSON data in request body::

    curl -H "Content-Type: application/json" -X POST -d '{"username":"admin","password":"admin"}' http://127.0.0.1:5000/login

Example 2, HTML form data::

    curl -X POST -H "Cache-Control: no-cache" -H "Content-Type: multipart/form-data" -F "username=admin" -F "password=admin" 'http://127.0.0.1:5000/login'

The response will provide the token to use in the next requests.

Example of answer::

    {
        "token": "1442583814636-bed32565-2ff7-4023-87fb-34a3ac93d34c"
    }

Generate new token (so revoke old)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to generate a new token (mean revoke old token), add this field to the request made
when you get the token:

* *action*: *generate*

Example::

    curl -H "Content-Type: application/json" -X POST -d '{"username":"admin","password":"admin","action":"generate"}' http://127.0.0.1:5000/login


How to use the token
~~~~~~~~~~~~~~~~~~~~

For all method you request on an endpoint, you need to provide the token.
You can use *basic auth*: use the token as a username and set password as empty.


GET method (get)
----------------

Get all available enpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~

All resources available in the backend are listed on the root endpoint of the backend::

    http://127.0.0.1:5000


All items
~~~~~~~~~

The endpoint to get all items of a resource is::

    http://127.0.0.1:5000/service

The items will be in response in section *_items*.

Curl example::

    curl -X GET -H "Content-Type: application/json"
    --user "1442583814636-bed32565-2ff7-4023-87fb-34a3ac93d34c:"
    http://127.0.0.1:5000/service


~~~~~~~~~~~~~~~~~~~~~
All items + filtering
~~~~~~~~~~~~~~~~~~~~~

We can filter items to get with this syntax::

    http://127.0.0.1:5000/service?where={"service_description": "ping"}

~~~~~~~~~~~~~~~~~~~
All items + sorting
~~~~~~~~~~~~~~~~~~~

We can sort items to get with this syntax::

    http://127.0.0.1:5000/service?sort=service_description

If you want to sort descending::

    http://127.0.0.1:5000/service?sort=-service_description

~~~~~~~~~~~~~~~~~~~~
All items + embedded
~~~~~~~~~~~~~~~~~~~~

In this example, service resource has data relation with host resource through the *host_name* field.
If you get items, you will receive an _id like *55d113976376e9835e1b2feb* in this field.

It's possible to have all fields of the host, instead of its _id, in the response with::

    http://127.0.0.1:5000/service?embedded={"host_name":1}

~~~~~~~~~~~~~~~~~~~~~~
All items + projection
~~~~~~~~~~~~~~~~~~~~~~

Projection is used to get only some fields for each items.
For example, to get only *service_description* of services::

    http://127.0.0.1:5000/service?projection={"service_description":1}

~~~~~~~~~~
Pagination
~~~~~~~~~~

The pagination is by default configured to 25 per request/page. It's possible to increase it to
the limit of 50 with::

    http://127.0.0.1:5000/service?max_results=50

In case of have many pages, in the items got, you have section::

    _links: {
        self: {
            href: "service",
            title: "service"
        },
        last: {
            href: "service?page=13",
            title: "last page"
        },
        parent: {
            href: "/",
            title: "home"
        },
        next: {
            href: "service?page=2",
            title: "next page"
        }
    },

So if you receive *_links/next*, there is a next page that can be found with *_links/next/href*.

~~~~~~~~~~~~~~~~
Meta information
~~~~~~~~~~~~~~~~

In the answer, you have a meta section::

    _meta: {
        max_results: 25,
        total: 309,
        page: 1
    }


One item
~~~~~~~~

To get only one item, we query with the *_id* in endpoint, like::

    http://127.0.0.1:5000/service/55d113976376e9835e1b3fee

It's possible in this case to use:

* projection_
* embedded_


.. _projection: #all-items-projection
.. _embedded: #all-items-embedded

POST method (add)
-----------------

This method is used to *create a new item*.
It's required to use HTTP *POST* method.

You need to point to the endpoint of the resource like::

    http://127.0.0.1:5000/service

and send JSON data like::

    {"service_description":"ping","notification_interval":60}

If you want to add a relation with another resource, you must add the id of the resource, like::

    {"service_description":"ping","notification_interval":60,"host_name":"55d113976376e9835e1b2feb"}

You will receive a response with the new *_id* and the *_etag* like::

    {"_updated": "Tue, 25 Aug 2015 14:10:02 GMT", "_links": {"self": {"href": "service/55dc773a6376e90ac95f836f", "title": "Service"}}, "_created": "Tue, 25 Aug 2015 14:10:02 GMT", "_status": "OK", "_id": "55dc773a6376e90ac95f836f", "_etag": "3c996dc10cb86173fa79f807e0d84e88c2f3a28f"}


PATCH method (update)
---------------------

This method is used to *update fields* of an item.
It's required to use HTTP *PATCH* method.

You need to point to the item endpoint of the resource like::

    http://127.0.0.1:5000/service/55dc773a6376e90ac95f836f

You need to add in headers the *_etag* you got when adding the object or when you got data of this item::

    "If-Match: 3c996dc10cb86173fa79f807e0d84e88c2f3a28f"

and send JSON data like::

    {"service_description":"pong"}


DELETE method (delete)
----------------------

It's required to use HTTP *DELETE* method.

All items
~~~~~~~~~

The endpoint to delete all items of a resource is::

    http://127.0.0.1:5000/service

One item
~~~~~~~~

The endpoint to delete an item of a resource is::

    http://127.0.0.1:5000/service/55dc773a6376e90ac95f836f
