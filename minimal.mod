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

SLOT 1 heater {
  DIO 1 [0,0];                                /* [source, direction] */
  DIO 2 [0,0];
  DIO 3 [0,0];
  DIO 4 [0,0];
  DIO 5 [0,0];
  DIO 6 [0,0];
  DIO 7 [0,0];
  DIO 8 [0,0];
  DIOPOWER = enabled;                         /* {enabled,disabled} or {0,1} */
  SENSOR A [0,0,-50,0,0] "sensorA";           /* [type,current,lolim,hilim,filter] "label" */
  HTR A [-100,A,25,5,force,1] "heaterA";      /* [target,sensor,vlimit,vforcelevel,force,enable] "label" */
  PID A [10,100,1,0];                         /* [P,I,D,I_limit] */
  RAMP A [1,disabled];                        /* [ramprate,enable] */
  SENSOR B [0,0,-50,0,0] "sensorB";           /* [type,current,lolim,hilim,filter] "label" */
  HTR B [-100,A,25,0,normal,1] "heaterB";     /* [target,sensor,vlimit,vforcelevel,force,enable] "label" */
  PID B [10,100,1,0];                         /* [P,I,D,I_limit] */
  RAMP B [1,disabled];                        /* [ramprate,enable] */
  UPDATETIME = 1000;                          /* update time for control loops in msec */
}

SLOT 3 lvds {
  DIO 1 [0,0] "LVDS_DIO_1";
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
  HVLC 1  [ResetDrain,0] "ResetDrain_4G"; /* Reset Drain 4 G */
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
  HVHC  1 [0,100,0,0] "ResetGateLow"; /* Reset Gate Low  */
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
  DRV 1 [Rphi_slew_fast,Rphi_slew_slow,1] "mydriver";
  DRV 2 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 3 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 4 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 5 [SW_slew_fast,SW_slew_slow,1];
  DRV 6 [Rphi_slew_fast,Rphi_slew_slow,1];
  DRV 7 [TG_slew_fast,TG_slew_slow,1];
  DRV 8 [Rphi_slew_fast,Rphi_slew_slow,1];
}

/* This is a LVbias card, maybe have to put in wdl  */
SLOT 12 lvbias {
  LVLC 1  [0,0];  /* Spare                           */
  LVLC 2  [0,0];  /* Spare                           */
  LVLC 3  [0,0];  /* Spare                           */
  LVLC 4  [0,0];  /* Spare                           */
  LVLC 5  [0,0];  /* Spare                           */
  LVLC 6  [0,0];  /* Spare                           */
  LVLC 7  [0,0];  /* Spare                           */
  LVLC 8  [0,0];  /* Spare                           */
  LVLC 9  [0,0];  /* Spare                           */
  LVLC 10 [0,0];  /* Spare                           */
  LVLC 11 [0,0];  /* Spare                           */
  LVLC 12 [0,0];  /* Spare                           */
  LVLC 13 [0,0];  /* Spare                           */
  LVLC 14 [0,0];  /* Spare                           */
  LVLC 15 [0,0];  /* Spare                           */
  LVLC 16 [0,0];  /* Spare                           */
  LVLC 17 [0,0];  /* Spare                           */
  LVLC 18 [0,0];  /* Spare                           */
  LVLC 19 [0,0];  /* Spare                           */
  LVLC 20 [0,0];  /* Spare                           */
  LVLC 21 [0,0];  /* Spare                           */
  LVLC 22 [0,0];  /* Spare                           */
  LVLC 23 [0,0];  /* Spare                           */
  LVLC 24 [1,0]; /* Output Transfer Gate            */
  LVHC  1 [RGLow,10,0,1];   /* Reset Gate Low Rail   */
  LVHC  2 [SWLow,10,0,1];   /* Summing Well Low Rail */
  LVHC  3 [0,100,0,1]; /* Spare                      */
  LVHC  4 [0,100,0,1]; /* Spare                      */
  LVHC  5 [0,100,0,1]; /* Spare                      */
  LVHC  6 [0,100,0,1]; /* Spare                      */
  DIO 1 [0,0] "mylabel";                                /* [source, direction] "label */
  DIO 2 [0,0];
  DIO 3 [0,0];
  DIO 4 [0,0];
  DIO 5 [0,0];
  DIO 6 [0,0];
  DIO 7 [0,0];
  DIO 8 [0,0];
}

