#! /usr/bin/env python

import param

if __name__ == '__main__':
    """
    desc

    Args:
    Returns:
    """

    import argparse
    import sys


    p = param.getStdParam(['CovBand', 'OrientBand', 'Marker', 'CovType', 'DataSegment', 'Prefix',
                            'XBounds', 'YBounds', 'ZBounds', 'ImageStep', 'Model', 'ImageDirectory',
                            'Mu', 'Pinv', 'MRIDirectory', 'ImageMetric'])

    parser = argparse.ArgumentParser(prog='main')
    parser.add_argument('-d', '--DataSet', action="store", dest="DataSet", required=True, help='Dataset path.')
    parser.add_argument('-p', '--ParamFile', action="store", dest="ParamFile", required=True, help='Parameter file name.')
    parser.add_argument('-v', '--Verbose', action="store_true", dest="Verbose", required=False, help='Be verbose.')
    parser.add_argument('-i', '--mridir', action="store", dest="MRIDirectory", required=False, help='MRI root.')

    try:
        parser.parse_args(namespace = p)
        p.parseFile(p.ParamFile)
    except Exception as e:
        p.err(e)

    print(p.CovBand)
    print(p.DataSegment)
