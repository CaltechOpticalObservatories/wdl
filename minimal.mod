/** -*- C -*- **/

/* Copyright (C) <2018> California Institute of Technology
* Software written by: <Dave Hale and Peter Mao>
* 
*     This program is part of the Waveform Definition Language (WDL) developed
*     for ZTF.  This program is free software: you can redistribute it and/or
*     modify it under the terms of the GNU General Public License as published
*     by the Free Software Foundation, either version 3 of the License, or
*     any later version.
* 
*     This program is distributed in the hope that it will be useful,
*     but WITHOUT ANY WARRANTY; without even the implied warranty of
*     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*     GNU General Public License for more details.
* 
*     Please see the GNU General Public License at:
*     <http://www.gnu.org/licenses/>.
* 
*     Report any bugs or suggested improvements to:
* 
*     David Hale <dhale@caltech.edu> or
*     Stephen Kaye <skaye@caltech.edu>
*/

#define	Iphi_slew_fast	10
#define Iphi_slew_slow	1
/*#define Rphi_slew_fast	500 /* default value on 20170630 */
/*#define Rphi_slew_slow	450 /* per experiments of 20170630 */
#define Rphi_slew_fast	100 /* 500 was too fast */
#define Rphi_slew_slow	105 /*  */
#define TG_slew_fast	400
#define TG_slew_slow	100
#define SW_slew_fast	100 /*40*/ /* 500 was too fast changed on 07/07/2017 */
#define SW_slew_slow	100 /*40*/

#define ResetDrain      17
#define ResetGateLow    5 /*5*/
#define ResetGateHi     12
/*#include ztf_science.def*/

SLOT 3 lvds {
  DIO 1 [0,0];
  DIO 2 [0,0];
  DIO 3 [0,0];
  DIO 4 [0,0];
  DIOPOWER = 0;
}

SLOT 4 driver {
  DRV 1 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 2 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 3 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 4 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 5 [SW_slew_fast,SW_slew_slow,1];
  DRV 6 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 7 [TG_slew_fast,TG_slew_slow,1];
  DRV 8 [Rphi_slew_fast,Rphi_slew_slow,1];
}

SLOT 5 ad {
  CLAMP 1 = -2.0;
  CLAMP 2 = -2.0;
  CLAMP 3 = -2.0;
  CLAMP 4 = -2.0;
  PREAMPGAIN = low;
}

SLOT 6 ad {
  CLAMP 1 = -2.0;
  CLAMP 2 = -2.0;
  CLAMP 3 = -2.0;
  CLAMP 4 = -2.0;
  PREAMPGAIN = low;
}

SLOT 7 ad {
  CLAMP 1 = -2.0;
  CLAMP 2 = -2.0;
  CLAMP 3 = -2.0;
  CLAMP 4 = -2.0;
  PREAMPGAIN = low;
}

SLOT 8 ad {
  CLAMP 1 = -2.0;
  CLAMP 2 = -2.0;
  CLAMP 3 = -2.0;
  CLAMP 4 = -2.0;
  PREAMPGAIN = low;
}

SLOT 9 hvbias {
  HVLC 1  [ResetDrain,0]; /* Reset Drain 4 G */
  HVLC 2  [ResetDrain,0]; /* Reset Drain 4 F */
  HVLC 3  [ResetDrain,0]; /* Reset Drain 4 E */
  HVLC 4  [ResetDrain,0]; /* Reset Drain 3 H */
  HVLC 5  [ResetDrain,0]; /* Reset Drain 3 G */
  HVLC 6  [ResetDrain,0]; /* Reset Drain 3 F */
  HVLC 7  [ResetDrain,0]; /* Reset Drain 3 E */
  HVLC 8  [ResetDrain,0]; /* Reset Drain 2 H */
  HVLC 9  [ResetDrain,0]; /* Reset Drain 2 G */
  HVLC 10 [ResetDrain,0]; /* Reset Drain 1 H */
  HVLC 11 [ResetDrain,0]; /* Reset Drain 2 E */
  HVLC 12 [ResetDrain,0]; /* Reset Drain 2 F */
  HVLC 13 [ResetDrain,0]; /* Reset Drain 4 H */
  HVLC 14 [2.5,0];/* Output Gate CCD1 */
  HVLC 15 [2.5,0];/* Output Gate CCD2 */
  HVLC 16 [2.5,0];/* Output Gate CCD3 */
  HVLC 17 [2.5,0];/* Output Gate CCD4 */
  HVLC 18 [25,0]; /* Dump Drain CCD1, CCD2 */  /* Note: relative to _PAR_CLOCK_LOW */
  HVLC 19 [ResetDrain,0]; /* Reset Drain 1 E */
  HVLC 20 [25,0]; /* Dump Drain CCD3, CCD4 */  /* Note: relative to _PAR_CLOCK_LOW */
  HVLC 21 [ResetDrain,0]; /* Reset Drain 1 F */
  HVLC 22 [0,0];  /* Dump Gate CCD3, CCD4 */
  HVLC 23 [ResetDrain,0]; /* Reset Drain 1 G */
  HVLC 24 [0,0];  /* Dump Drain CCD1, CCD2 */
  HVHC  1 [0,100,0,0]; /* Reset Gate Low  */
  HVHC  2 [0,100,0,0];/* Reset Gate High */
  HVHC  3 [0,100,0,0];/* Output Drain CCD4 */
  HVHC  4 [0,100,0,0];/* Output Drain CCD1 */
  HVHC  5 [0,100,0,0];/* Output Drain CCD2 */
  HVHC  6 [0,100,0,0];/* Output Drain CCD3 */
}

SLOT 10 driver {
  DRV 1 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 2 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 3 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 4 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 5 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 6 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 7 [Iphi_slew_fast,Iphi_slew_slow,1];
  DRV 8 [Iphi_slew_fast,Iphi_slew_slow,1];
}

SLOT 11 driver {
  DRV 1 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 2 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 3 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 4 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 5 [SW_slew_fast,SW_slew_slow,1];
  DRV 6 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 7 [TG_slew_fast,TG_slew_slow,1];
  DRV 8 [Rphi_slew_fast,Rphi_slew_slow,1];
}

