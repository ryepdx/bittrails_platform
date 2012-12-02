import pyRserve
import numpy

def getCorrelationMatrix(*args):
	# connect to Rserve (running as daemon process - configured for port 9999)
	# to start run on command line 'R CMD Rserve --RS-port 9999'
	conn = pyRserve.connect(host='localhost',port=9999)

	# combine streams by column - will create a matrix with dimensions = #ofstreams by number of elements
	#inputDataStreams = conn.r.cbind(stream1,stream2,stream3,stream4)
	inputDataStreams = conn.r.cbind(*args)
	#print(inputDataStreams)

	# Create a correlation matrix based on input streams
	corrMatrix = conn.r.cor(inputDataStreams)
	#print(corrMatrix)

	# Always good to close connections
	conn.close()
	return corrMatrix
