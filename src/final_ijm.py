import json

def ijm_main(doc, args=None):
    """ load JSON, clip the content and change values """
    args = args or {}
    # convert to json
    article_json = json.loads(doc.read())
    # take only the article content
    article_json_article = article_json["article"]
    article_text = json.dumps(article_json_article, indent=4)
    # replace the iiif server uri
    return article_text.replace('https://example.org/iiif/2', '%iiif_uri%')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', type=argparse.FileType('r'))
    args = vars(parser.parse_args())
    doc = args.pop('infile')
    print(ijm_main(doc, args))
