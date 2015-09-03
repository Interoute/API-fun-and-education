API programming for fun and education: Programs from the Interoute CloudStore blogs
===================================================================================

This repository contains programs used and described in blog posts written by Phillip Kent about [Interoute Virtual Data Centre](https://cloudstore.interoute.com/what_is_vdc) and using the API programming interface.

Index of blog posts: http://cloudstore.interoute.com/blogs/PhillipKent

API configuration file
----------------------

API access details should be included in a configuration file. The default location for this is a file named '.vdcapi' in your home directory. The contents of the configuration file should look like this:

    {"api_secret":"n3P50xlPa7IfiA1L7s7hWQplkqHdvkG37tS7ljLZb4X4gpCzKdn93Lu-uEFTUV4h9zboWvCXuvlVcQZeEy9-hg",
     "api_key":"HHf9osXIUeIkEUzD__7emXOPuDRug6mpTIVnqDaSIK6NjlwDzq7V0QhvQSil_yk74m9HjIQny7Rb0sgeMsD90B",
     "api_url": "http://server.example.com/path/to/api"}