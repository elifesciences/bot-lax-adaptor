import io
import sys
import adaptor

if __name__ == '__main__':
    args = sys.argv[1:]
    inloc, outloc = args
    with io.open(outloc, 'w', encoding='utf-8') as fh:
        fh.write(adaptor.download(inloc))
