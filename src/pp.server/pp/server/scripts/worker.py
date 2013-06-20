import os
import plac
import time
import multiprocessing


def main():
    prepare_pool = multiprocessing.Pool(30)
    while 1:
        print '1' 
        time.sleep(5)


if __name__ == '__main__':
    main()

