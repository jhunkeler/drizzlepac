from __future__ import print_function
import os,glob
import shutil
import filecmp
try:
    import urllib.request as req
except ImportError:
    import urllib as req

import nose.tools

import pandokia.helpers.process as process
import pandokia.helpers.filecomp as filecomp

from stsci.tools import testutil
from stsci.tools import teal
from drizzlepac import astrodrizzle
from stwcs import updatewcs

#
# The old xml tests contain a single test in a <regtest> block.
# We write that as a test in python.  The most convenient way to do
# it is as a test function.  This works with both nose and py.test
#
remote = {}
remote['base'] = 'http://ssb.stsci.edu/cgi-bin/remote_testing.cgi'
remote['tree'] = 'rt'
remote['project'] = 'betadrizzle'
remote['name'] = 'orig/stis/stis_01'

datastruct = {}
datastruct['prefix'] = 'o60q02f'
datastruct['suffix'] = 'q_flt.fits'
datastruct['unique'] = ['4', '6', '8', 'b', 'c', 'e', 'g', 'i']
datastruct['cfg'] = ['reference.fits', 'final_drz.fits', 'astrodrizzle.cfg']


def construct_urls():
    global remote
    global datastruct
    r = remote
    d = datastruct
    urls = []
    for key in d['unique']:
        filename = d['prefix'] + key + d['suffix']
        url = r['base'] + '?' + '&'.join(['tree=' + r['tree'], 'project=' + r['project'], 'name=' + os.path.join(r['name'], filename)])
        urls.append(url)

    #for cfg in d['cfg']:
    #    filename = cfg
    #    r['name'] = r['name'].replace('orig/','')
    #    url = r['base'] + '?' + '&'.join(['tree=' + r['tree'], 'project=' + r['project'], 'name=' + os.path.join(r['name'], filename)])
    #    urls.append(url)

    return urls

def download_data(url):
    filename = os.path.basename(url)
    print('Retrieving {0}... '.format(url), end='')
    req.urlretrieve(url, filename)
    print('done')


@nose.tools.istest
def stis_01():
    urls = construct_urls()
    for u in urls:
        download_data(u)

    # Even though the test is named after the test function, we
    # still need a string for the test name.  We use it later.
    testname = 'stis_01_1visit'

    # Define root directory for original input files
    #orig_root = "../../orig/stis/stis_01"

    # You need to have a tda dict for:
    #  - recording information to make FlagOK work
    #  - recording parameters to the task as attributes
    #global tda
    #tda = { }
    #tra = { }

    output = [
        # one dict for each output file to compare (i.e. each <val>)
        {
            'file'      : 'final_drz.fits',
            'reference' : 'reference.fits',
            'comparator': 'image',
            'args'      : {
            'ignorekeys': [ 'origin,filename,date,iraf-tlm,fitsdate,prod_ver,\
                                upwtim,wcscdate,upwcsver,pywcsver,rulefile,history'
                            ],
            'maxdiff': 1e-7,

             },

        },
        # if there are more files, list more dicts here
    ]
    # delete all the output files before starting the test
    filecomp.delete_output_files( output )

    # Start by cleaning up any files left behind from the last test run
    filecomp.wild_rm([ "o*.fits", "*coeffs*", "*.log" ])

    # copy in fresh versions of the input files
    #for f in glob.glob(os.path.join(orig_root,'o60q02*flt.fits')):
    #    fpath,froot = os.path.split(f)
    #    shutil.copyfile(f,froot)

    # load astrodrizzle configuration parameters:
    parObj = teal.load('astrodrizzle.cfg')

    # update input images with new distortion model reference file names only
    updatewcs.updatewcs(parObj['input'])

    # run astrodrizzle now...
    astrodrizzle.AstroDrizzle('o*flt.fits',runfile=testname,configobj=parObj)

    # Clean-up after running the task...
    filecomp.wild_rm([ "*mask.fits", "*blt.fits", "*cor.fits", "*med.fits",
                       "*single*.fits", "tmp*ask.fits",
                       "tmp*_skymatch_mask_*.fits" ])

    # report the contents of the log file
    testutil.dump_all_log_files()

    # compare the output files - use this exact command
    #filecomp.compare_files( output, ( __file__, testname ), tda = tda,)
    filecmp.cmp()


if __name__ == '__main__':
    urls = construct_urls()
    for u in urls:
        download_data(u)
