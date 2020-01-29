"""Basic namespace, just to test things out.

"""

from io import StringIO

import fs
from fs import memoryfs

from hashfs import HashFS

ROOT = '/Users/samritchie/.modeldb'
# Set the `depth` to the number of subfolders the file's hash should be split
# when saving. Set the `width` to the desired width of each subfolder.

# With depth=4 and width=1, files will be saved in the following pattern:
# temp_hashfs/a/b/c/d/efghijklmnopqrstuvwxyz

# With depth=3 and width=2, files will be saved in the following pattern:
# temp_hashfs/ab/cd/ef/ghijklmnopqrstuvwxyz


def persist(i):
    """Add a docstring."""
    myfs = fs.open_fs(ROOT)
    memfs = fs.memoryfs.MemoryFS()
    print(memfs.tree())

    from io import BytesIO
    some_content = BytesIO(b'some content')

    # This is how to write this shit out!
    print(myfs.makedirs('/face/cake', recreate=True))
    print(myfs.writefile('/face/cake/hammer', some_content))
    print(memfs.tree())
    print(myfs.tree())

    filesystem = HashFS(memfs, depth=2, width=2, algorithm='sha256')

    # address = filesystem.put(some_content)
    # print(address)

    # more_content = StringIO('more content')
    # address2 = filesystem.put(more_content)

    # for f in filesystem.folders():
    #     print(f)

    # print("and others...")

    # print(list(filesystem.files()))
    # print(list(filesystem.folders()))

    # print(address)
    # print(address2)


if __name__ == '__main__':
    persist(1)
