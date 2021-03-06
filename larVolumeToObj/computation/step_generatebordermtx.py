# -*- coding: utf-8 -*-

from lar import *
from scipy import *
import json
import scipy
import numpy as np
import time as tm
import gc
import struct
import sys
import getopt, sys
import traceback
import os

import logging
logger = logging.getLogger(__name__)
# ------------------------------------------------------------
# Logging & Timer
# ------------------------------------------------------------

logging_level = 0

# 0 = no_logging
# 1 = few details
# 2 = many details
# 3 = many many details

def log(n, l):
    if __name__=="__main__" and n <= logging_level:
        for s in l:
            print "Log:", s

timer = 1

timer_last =  tm.time()

def timer_start(s):
    global timer_last
    if __name__=="__main__" and timer == 1:
        log(3, ["Timer start:" + s])
    timer_last = tm.time()

def timer_stop():
    global timer_last
    if __name__=="__main__" and timer == 1:
        log(3, ["Timer stop :" + str(tm.time() - timer_last)])

# ------------------------------------------------------------
# Computation of ∂3 operator on the image space
# ------------------------------------------------------------

def invertIndex(nx,ny,nz):
    nx,ny,nz = nx+1,ny+1,nz+1
    def invertIndex0(offset):
        a0, b0 = offset / nx, offset % nx
        a1, b1 = a0 / ny, a0 % ny
        a2, b2 = a1 / nz, a1 % nz
        return b0,b1,b2
    return invertIndex0


def computeBordo3(FV,CV,inputFile='bordo3.json'):
    log(1, ["bordo3 = Starting"])
    bordo3 = larBoundary(FV,CV)
    log(3, ["bordo3 = " + str(bordo3)])
    log(1, ["bordo3 = Done"])

    ROWCOUNT = bordo3.shape[0]
    COLCOUNT = bordo3.shape[1]
    ROW = bordo3.indptr.tolist()
    COL = bordo3.indices.tolist()
    # DATA = bordo3.data.tolist()

    with open(inputFile, "w") as file:
        json.dump({
            "ROWCOUNT":ROWCOUNT, "COLCOUNT":COLCOUNT, "ROW":ROW,
            "COL":COL, "DATA":1}, file, separators=(',',':'))
        # json.dump({"ROWCOUNT":ROWCOUNT, "COLCOUNT":COLCOUNT, "ROW":ROW, "COL":COL, "DATA":DATA }, file, separators=(',',':'))
        file.flush();


def orientedBoundaryCells(V, (VV, EV, FV, CV)):

    from larcc import signedCellularBoundary
    boundaryMat = signedCellularBoundary(V, [VV, EV, FV, CV])
    chainCoords = scipy.sparse.csc_matrix((len(CV), 1))
    for cell in range(len(CV)):
        chainCoords[cell, 0] = 1
    boundaryCells = list((boundaryMat * chainCoords).tocoo().row)
    orientations = list((boundaryMat * chainCoords).tocoo().data)
    return zip(orientations, boundaryCells)


def orientedBoundaryCellsFromBM(boundaryMat, lenCV):
    """
    part of orientedBoundaryCells
    """
    chainCoords = scipy.sparse.csc_matrix((lenCV, 1))
    for cell in range(lenCV):
        chainCoords[cell, 0] = 1
    boundaryCells = list((boundaryMat * chainCoords).tocoo().row)
    orientations = list((boundaryMat * chainCoords).tocoo().data)
    return zip(orientations, boundaryCells)


def normalVector(V, facet):
    v0, v1, v2 = facet[:3]
    return VECTPROD([DIFF([V[v1], V[v0]]), DIFF([V[v2], V[v0]])])


def orientedQuads(FV, boundaryCellspairs):
    from larcc import swap

    orientedQuads = [
        [sign, swap(FV[face])[::-1]] if sign > 0
        else [sign, swap(FV[face])]
        for (sign, face) in boundaryCellspairs]

    # orientedQuads = []
    # for (sign, face) in boundaryCellspairs:
    #     if sign > 0:
    #         # orientedQuads.append([sign, FV[face]])
    #         orientedQuads.append([sign, swap(FV[face])[::-1]])
    #         pass
    #     else:
    #         # [v1, v2, v3, v4] =
    #         # orientedQuads.append([sign, FV[face][::-1]])
    #         orientedQuads.append([sign, swap(FV[face])])

    return orientedQuads


def computeOrientedBordo3(nx, ny, nz):
    # from py.computation.lar import si
    from larcc import signedCellularBoundary
    # bordo3 = larBoundary(FV,CV)
    V, [VV, EV, FV, CV] = getBases(nx, ny, nz)
    boundaryMat = signedCellularBoundary(V, [VV, EV, FV, CV])
    return boundaryMat


def writeBordo3(bordo3, inputFile):
    ROWCOUNT = bordo3.shape[0]
    COLCOUNT = bordo3.shape[1]
    ROW = bordo3.indptr.tolist()
    COL = bordo3.indices.tolist()
    DATA = bordo3.data.tolist()

    with open(inputFile, "w") as file:
        json.dump({
            "ROWCOUNT": ROWCOUNT, "COLCOUNT": COLCOUNT,
            "ROW": ROW, "COL": COL, "DATA": DATA}, file,
            separators=(',', ':'))
        file.flush()


def getOrientedBordo3Path(nx, ny, nz, DIR_OUT):
    """
    Function try read boro3 from file. If it fail. Matrix is computed
    """

    fileName = DIR_OUT+'/bordo3_'+str(nx)+'-'+str(ny)+'-'+str(nz)+'.json'
    if os.path.exists(fileName):
        logger.info('used old bordermatrix')
    else:
        logger.info("generating new border matrix")
        V, bases = getBases(nx, ny, nz)
        VV, EV, FV, CV = bases
        # bordo3 = computeBordo3(FV,CV,inputFile=fileName)
        brodo3 = computeOrientedBordo3(nx, ny, nz)
        writeBordo3(brodo3, fileName)
    return fileName


def getBases(nx, ny, nz):

    def ind(x,y,z): return x + (nx+1) * (y + (ny+1) * (z))

    def the3Dcell(coords):
        x,y,z = coords
        return [ind(x,y,z),ind(x+1,y,z),ind(x,y+1,z),ind(x,y,z+1),ind(x+1,y+1,z),
                ind(x+1,y,z+1),ind(x,y+1,z+1),ind(x+1,y+1,z+1)]

    # Construction of vertex coordinates (nx * ny * nz)
    # ------------------------------------------------------------

    try:
        V = [[x,y,z] for z in xrange(nz+1) for y in xrange(ny+1) for x in xrange(nx+1) ]
    except:
        import ipdb; ipdb.set_trace() #  noqa BREAKPOINT


    log(3, ["V = " + str(V)])

    # Construction of CV relation (nx * ny * nz)
    # ------------------------------------------------------------

    CV = [the3Dcell([x,y,z]) for z in xrange(nz) for y in xrange(ny) for x in xrange(nx)]

    log(3, ["CV = " + str(CV)])

    # Construction of FV relation (nx * ny * nz)
    # ------------------------------------------------------------

    FV = []

    v2coords = invertIndex(nx,ny,nz)

    for h in xrange(len(V)):
        x,y,z = v2coords(h)
        if (x < nx) and (y < ny): FV.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
        if (x < nx) and (z < nz): FV.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
        if (y < ny) and (z < nz): FV.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

    VV = AA(LIST)(range(len(V)))

    EV = []
    for h in xrange(len(V)):
        x,y,z = v2coords(h)
        if (x < nx): EV.append([h,ind(x+1,y,z)])
        if (y < ny): EV.append([h,ind(x,y+1,z)])
        if (z < nz): EV.append([h,ind(x,y,z+1)])

    # return V, FV, CV, VV, EV
    return V, (VV, EV, FV, CV)

def main(argv):
    ARGS_STRING = 'Args: -x <borderX> -y <borderY> -z <borderZ> -o <outputdir>'

    try:
        opts, args = getopt.getopt(argv,"o:x:y:z:")
    except getopt.GetoptError:
        print ARGS_STRING
        sys.exit(2)

    mandatory = 2
    #Files
    DIR_OUT = ''

    for opt, arg in opts:
        if opt == '-x':
            nx = ny = nz = int(arg)
            mandatory = mandatory - 1
        elif opt == '-y':
            ny = nz = int(arg)
        elif opt == '-z':
            nz = int(arg)
        elif opt == '-o':
            DIR_OUT = arg
            mandatory = mandatory - 1

    if mandatory != 0:
        print 'Not all arguments where given'
        print ARGS_STRING
        sys.exit(2)

    log(1, ["nx, ny, nz = " + str(nx) + "," + str(ny) + "," + str(nz)])

    V, bases = getBases(nx, ny, nz)
    VV, EV, FV, CV = bases
    log(3, ["FV = " + str(FV)])

    fileName = DIR_OUT+'/bordo3_'+str(nx)+'-'+str(ny)+'-'+str(nz)+'.json'

    try:
        computeBordo3(FV,CV,fileName)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])  # Log it or whatever here
        sys.exit(2)

if __name__ == "__main__":
    main(sys.argv[1:])
