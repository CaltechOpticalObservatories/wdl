modulefile Demo.mod
signalfile Demo.signals

sequence Main:
if Expose CALL GrabFrame
if test_mode CALL TestPhase
GOTO Main

sequence TestMode:
CALL wFrame
CALL wLine
CALL wPixel
CALL TestPhase(100)
RETURN TestMode

sequence TestRG:
CALL OnlyRG_Hi
CALL Sec(5)
CALL OnlyRG_Lo
CALL Sec(5)
RETURN TestRG

sequence TestSW:
CALL OnlySW_Hi
CALL Sec(5)
CALL TestRG
CALL OnlySW_Lo
CALL Sec(5)
CALL TestRG
RETURN TestSW

sequence GrabFrame:
Expose--
CALL ParallelShiftMPP(4096)
CALL Sec(exptime)
CALL wFrame
CALL GrabLine(1000)
RETURN GrabFrame

sequence GrabLine:
CALL wLine
CALL ClampAC
CALL ParallelShiftMPP
CALL GrabPixel(2118)
RETURN GrabLine

sequence GrabPixel:
CALL wPixel
CALL SerialShiftPixelB
CALL wDelay1us
RETURN GrabPixel

sequence MilliSec:
CALL wDelay1ms
RETURN MilliSec

sequence Sec:
CALL MilliSec(1000)
RETURN Sec

waveform RawPixel:
1000 RETURN RawPixel

waveform wDelay1us:
100 RETURN wDelay1us

waveform wDelay1ms:
100000 RETURN wDelay1ms

waveform wSampleDelay:
1000 RETURN wSampleDelay

waveform SerialShiftPixelA:
0 12 0 0.0
0 12 2 1.0
0 2 18 3.8
0 2 19 1
300 2 14 -5.0
300 2 15 1
600 12 0 1.0
600 2 22 3.8
600 2 23 1
600 12 1 0.0
900 2 18 -5.0
900 2 19 1
1900 12 2 0.0
2200 2 14 3.8
2200 2 15 1
2500 2 22 -5.0
2500 2 23 1
2500 12 1 1.0
3500 RETURN SerialShiftPixelA

waveform SerialShiftPixelB:
0 12 0 0.0
300 12 0 0.0
600 12 0 1.0
900 12 1 0.0
900 2 22 3.8
900 2 23 1
1200 2 14 -5.0
1200 2 15 1
1500 2 18 3.8
1500 2 19 1
1800 2 22 -5.0
1800 2 23 1
2100 2 14 3.8
2100 2 15 1
2400 2 18 -5.0
2400 2 19 1
2700 12 2 1.0
3700 12 2 0.0
4000 12 1 1.0
4300 RETURN SerialShiftPixelB

waveform OnlyRG_Hi:
0 12 0 0.0
300 RETURN OnlyRG_Hi

waveform OnlyRG_Lo:
0 12 0 1.0
300 RETURN OnlyRG_Lo

waveform OnlySW_Hi:
0 12 1 0.0
300 RETURN OnlySW_Hi

waveform OnlySW_Lo:
0 12 1 1.0
300 RETURN OnlySW_Lo

waveform ParallelShiftMPP:
0 2 6 2.0
0 2 7 1
40000 2 10 5.8
40000 2 11 1
80000 2 6 -10.0
80000 2 7 1
120000 2 2 2.0
120000 2 3 1
160000 2 10 -7.8
160000 2 11 1
200000 2 2 -10.0
200000 2 3 1
240000 RETURN ParallelShiftMPP

waveform ClampAC:
0 12 2 1.0
1000 12 2 0.0
1300 RETURN ClampAC

waveform TestPhase:
0 12 0 0.0
300 12 0 1.0
600 2 14 3.8
600 2 15 1
900 2 14 -5.0
900 2 15 1
1200 2 18 3.8
1200 2 19 1
1500 2 18 -5.0
1500 2 19 1
1800 2 22 3.8
1800 2 23 1
2100 2 22 -5.0
2100 2 23 1
2400 12 1 0.0
2700 12 1 1.0
3000 2 2 2.0
3000 2 3 1
3300 2 2 -10.0
3300 2 3 1
3600 2 6 2.0
3600 2 7 1
3900 2 6 -10.0
3900 2 7 1
4200 2 10 5.8
4200 2 11 1
4500 2 10 -7.8
4500 2 11 1
4800 12 2 1.0
5800 12 2 0.0
45800 RETURN TestPhase

waveform RGHi:
0 12 0 0.0
300 RETURN RGHi

waveform wFrame:
0 0 1 1.0
1 RETURN wFrame

waveform wLine:
0 0 2 1.0
1 RETURN wLine

waveform wPixel:
0 0 3 1.0
1 0 3 0.0
1 0 1 0.0
1 0 2 0.0
2 RETURN wPixel

parameter Expose=0
parameter exptime=0
parameter test_mode=0
parameter longexposure=0

