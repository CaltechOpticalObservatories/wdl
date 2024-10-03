modulefile minimal.mod
signalfile minimal.signals

sequence Start:
CALL Clock

waveform Clock:
0 4 0 1.25
0 4 1 1.25
0 4 0 1.25
0 4 1 1.25
2 4 0 -2.75
2 4 1 -2.75
2 4 0 -2.75
2 4 1 -2.75
3 RETURN Clock

waveform Clock1:
0 4 0 1.25
0 4 1 1.25
2 4 0 -2.75
2 4 1 -2.75
3 RETURN Clock1

parameter exptime=0
parameter Expose=0
parameter Readout=0

