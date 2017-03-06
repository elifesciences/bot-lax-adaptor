import adaptor, fs_adaptor, utils
import json

# not working, untested

def main():
    cmd = [
        adaptor.find_lax(), # /srv/lax/manage.sh
        "status",
        "article-versions.invalid-unpublished.list"
    ]
    lax_stdout = None
    rc, lax_stdout = utils.run_script(cmd)

    requests = []
    for av in json.loads(lax_stdout)['article-versions.invalid-unpublished.list']:
        # ll:
        # {
        #   'msid': 25532,
        #   'version': 2,
        #   'location': "https://s3.amazonaws.com/elife-publishing-expanded/25532.2/7f768a31-95e6-452d-9b86-2fdc2150a3fe/elife-25532-v2.xml"
        # }
        requests.append(fs_adaptor.mkreq(path=av['location']))

    incoming = fs_adaptor.SimpleQueue(path_list=requests)
    outgoing = fs_adaptor.OutgoingQueue()

    adaptor.do(incoming, outgoing)
