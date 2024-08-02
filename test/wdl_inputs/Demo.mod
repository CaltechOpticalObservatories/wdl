#include Demo.def

/* Nominal values for the biases */
#define VSPARE      0
#define VOPAMPPD    5.0
#define VLG         -3.4
#define VRG_HI      12
#define VRG_LO      4
#define VSW_HI      4
#define VSW_LO      -4
#define VRD         14
#define VOFD        14.9
#define VDD         24.1

SLOT 9 lvbias {
  LVLC 1  [VSPARE,1];
  LVLC 2  [VSPARE,1];         
  LVLC 3  [VSPARE,1];         
  LVLC 4  [VSPARE,1];
  LVLC 5  [VSPARE,1]; 
  LVLC 6  [VSPARE,1];         
  LVLC 7  [VSPARE,1];
  LVLC 8  [VSPARE,1];        
  LVLC 9  [VOPAMPPD,1] 'OPAMP Power Down'; 
  LVLC 10 [VSPARE,1];
  LVLC 11 [VLG,1] 'SITe Last Gate';     
  LVLC 12 [VSPARE,1];      
  LVLC 13 [VSPARE,1];
  LVLC 14 [VSPARE,1];   
  LVLC 15 [VRG_HI,1] 'Reset Gate High';        
  LVLC 16 [VSPARE,1];  
  LVLC 17 [VRG_LO,1] 'Reset Gate Low' ; 
  LVLC 18 [VSPARE,1];     
  LVLC 19 [VSW_HI,1] 'Summing Well High';   
  LVLC 20 [VSPARE,1];    
  LVLC 21 [VSW_LO,1] 'Summing Well Low';      
  LVLC 22 [VSPARE,1];        
  LVLC 23 [VSPARE,1];        /* Spare                  */
  LVLC 24 [VSPARE,1];        /* Spare                  */
  LVHC  1 [VSPARE,10,1,1];   /* Spare                  */
  LVHC  2 [VSPARE,50,1,1];   /*           */
  LVHC  3 [VSPARE,10,1,1];   /* Spare                  */
  LVHC  4 [VSPARE,100,1,1];  /*   */
  LVHC  5 [VSPARE,100,0,1];  /*                     */
  LVHC  6 [VSPARE,10,1,1];   /* Spare                  */
}

SLOT 10 hvbias {
  HVLC 1  [VSPARE,1];
  HVLC 2  [VSPARE,1];         
  HVLC 3  [VSPARE,1];         
  HVLC 4  [VSPARE,1];
  HVLC 5  [VSPARE,1]; 
  HVLC 6  [VSPARE,1];         
  HVLC 7  [VRD,1] 'Reset Drain';
  HVLC 8  [VSPARE,1];        
  HVLC 9  [VOFD,1] 'Overflow Drain'; 
  HVLC 10 [VSPARE,1];
  HVLC 11 [VSPARE,1];      
  HVLC 12 [VSPARE,1];     
  HVLC 13 [VSPARE,1];
  HVLC 14 [VSPARE,1];   
  HVLC 15 [VSPARE,1];        
  HVLC 16 [VSPARE,1];  
  HVLC 17 [VSPARE,1]; 
  HVLC 18 [VSPARE,1];     
  HVLC 19 [VSPARE,1];   
  HVLC 20 [VSPARE,1];    
  HVLC 21 [VSPARE,1];      
  HVLC 22 [VSPARE,1];        
  HVLC 23 [VSPARE,1];        /* Spare                  */
  HVLC 24 [VSPARE,1];        /* Spare                  */
  HVHC  1 [VDD,10,1,1]'V_dd';   /* Spare                  */
  HVHC  2 [VSPARE,50,1,1];   /*           */
  HVHC  3 [VSPARE,10,1,1];   /* Spare                  */
  HVHC  4 [VSPARE,100,1,1];  /*   */
  HVHC  5 [VSPARE,100,0,1];  /*                     */
  HVHC  6 [VSPARE,10,1,1];   /* Spare                  */
}

#define clock_fast 500
#define clock_slow 100

SLOT 2 driverx {
  DRVX 1 [clock_fast, clock_slow, 0]''; 
  DRVX 2 [clock_fast, clock_slow, 1]'P1';
  DRVX 3 [clock_fast, clock_slow, 0]'';
  DRVX 4 [clock_fast, clock_slow, 1]'P2';
  DRVX 5 [clock_fast, clock_slow, 0]'';
  DRVX 6 [clock_fast, clock_slow, 1]'P3';
  DRVX 7 [clock_fast, clock_slow, 0]'';
  DRVX 8 [clock_fast, clock_slow, 1]'S1';
  DRVX 9 [clock_fast, clock_slow, 0]'';
  DRVX 10 [clock_fast, clock_slow, 1]'S2';
  DRVX 11 [clock_fast, clock_slow, 0]'';
  DRVX 12 [clock_fast, clock_slow, 1]'S3';
}

SLOT 12 lvds {
}
