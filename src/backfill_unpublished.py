import adaptor, fs_adaptor, utils
import json

"""
invalid and unpublished articles will avoid a regular backfill because they are absent from the github repo.
when it comes time to publish them, they'll fail. 

this state comes about when: 
1. we allow invalid article-json on INGEST. 
this was the state for many months to ease the backpressure on production

2. we change what 'valid' means
our schema may change on us and what was once valid no longer is. 
if there are unpublished articles in lax when this happens, they will fail to publish.
"""

def invalid_unpublished_list_from_lax():
    "returns a list of articles that are invalid+unpublished after talking to lax."
    # lax has a 'status' report that will give us a list of unpublished + invalid articles
    cmd = [
        adaptor.find_lax(), # /srv/lax/manage.sh
        "status",
        "article-versions.invalid-unpublished.list"
    ]
    lax_stdout = None
    rc, lax_stdout = utils.run_script(cmd)
    ensure(rc == 0, "failed to talk with lax, got return code %r and stdout: %s" % (rc, lax_stdout))
    # ll: [{
    #   'msid': 25532,
    #   'version': 2,
    #   'location': "https://s3.amazonaws.com/elife-publishing-expanded/25532.2/7f768a31-95e6-452d-9b86-2fdc2150a3fe/elife-25532-v2.xml"
    # }, ... ]
    return json.loads(lax_stdout).get('article-versions.invalid-unpublished.list', [])

def send_ingest_requests_to_lax(request_list):
    "for each article we want to send a request "
    try:
        incoming = fs_adaptor.SimpleQueue(path_list=request_list)
        outgoing = fs_adaptor.OutgoingQueue()
        adaptor.do(incoming, outgoing)
        # ... ?
    finally:
        print "done"

def mkreq(lax_report_result):
    "wrangle some basic info into a proper request to lax"
    return fs_adaptor.mkreq(lax_report_result['location'])
    
def main():
    to_be_reingested = lmap(mkreq, invalid_unpublished_list_from_lax())
    send_ingest_requests_to_lax(to_be_reingested)

if __name__ == '__main__':
    main()
    exit(0)
