#!/bin/bash
# a demonstration on how to use the bot-lax api

# this will use curl to upload the xml file 'elife-00003-v1.xml'
# once uploaded, it will transform it to article-json, validate it then send it
# to lax. lax will trial ingesting it and respond with the results. lax will 
# roll back any changes made so no actual ingestion happens.

# the naming of the file is important, it must look like 'elife-XXXXX-vX.xml'

curl -X POST \
    --header 'Content-Type: multipart/form-data' \
    --header 'Accept: application/json' \
    --form 'xml=@article-xml/articles/elife-00003-v1.xml' \
    'https://lax.elifesciences.org:8001/xml'

# after a successful transformation from xml to article-json, even if lax 
# responds with an error, the result of the transformation can be downloaded 
# with:

curl -X GET \
    --header 'Accept: application/json' \
    'https://lax.elifesciences.org:8001/article-json/elife-00003-v1.xml.json'
    
# the name of the article-json to download is simply the name of the xml file 
# suffixed with '.json'

# to get a list of previous transformations available for download:

curl -X GET \
    --header 'Accept: application/json' 
    'https://lax.elifesciences.org:8001/article-json'
    
# overrides can be specified for top-level article-json attributes
# these are applied after the transformation occurs but before the result is
# sent to lax for validation.

# here, an override for 'authorLine' is being provided with a dummy value
# the key and value are separated with a pipe '|' and the value, because it's a
# string, is quoted:

curl -X POST \
    --header 'Content-Type: multipart/form-data' \
    --header 'Accept: application/json' \
    --form 'xml=@article-xml/articles/elife-00003-v1.xml' \
    --form 'override=authorLine|"fake value, sad"' \
    'https://lax.elifesciences.org:8001/xml'

# behind the scenes the value is converted to json. if you don't supply a valid
# json value, you are going to get an error response about not being able to 
# deserialize the given value. quote strings!

# multiple overrides can be applied:

curl -X POST \
    --header 'Content-Type: multipart/form-data' \
    --header 'Accept: application/json' \
    --form 'xml=@article-xml/articles/elife-00003-v1.xml' \
    --form 'override=volume|4' \
    --form 'override=type|"editorial"' \
    'https://lax.elifesciences.org:8001/xml'




