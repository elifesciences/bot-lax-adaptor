import io
import sys

import src.adaptor as adaptor

if __name__ == '__main__':
    inloc, outloc = sys.argv[1:3]
    with io.open(outloc, 'w', encoding='utf-8') as fh:
        fh.write(adaptor.download(inloc))
