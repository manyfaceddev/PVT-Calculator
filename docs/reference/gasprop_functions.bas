Attribute VB_Name = "GasProp Functions"
'******************************************************************************
' Compositional Gas properties correlations spreadsheet -- Version 1.0 95/11/29
' PROPRIETARY; Copyright Amoco Corporation 1995
' For exclusive use of Amoco and subsidiaries
'
' Written by E. A. Turek and R. W. Morris based on source code
' from pvtcalc and xblackoil programs
' Modified by W. L. Barnard to add compositional capability
'******************************************************************************

Option Explicit
Option Base 1
Const n_comps = 12

'******************************************************************************

Public Function HallYarbGasZ(ByVal ResTempF As Double, _
                             ByVal PresPsia As Double, _
                             ByVal Composition As Variant, _
                             ByVal C7plusMolWt As Double, _
                             ByVal C7plusDensGmCc As Double) _
  As Variant
Attribute HallYarbGasZ.VB_Description = "Calculate gas Z factor using the Hall-Yarborough correlation"
Attribute HallYarbGasZ.VB_ProcData.VB_Invoke_Func = " \n14"
                      
' Purpose:
'   Calculates gas Z factor based on gas gravity using the
'   Hall-Yarborough correlation
                      
  Dim tcmv  As Double, pcmv  As Double, vcmv As Double, amwv As Double
  Dim rrt   As Double
  Dim ea    As Double
  Dim eb    As Double
  Dim ec    As Double
  Dim ed    As Double
  Dim ef    As Double
  Dim ey    As Double
  Dim rp    As Double
  Dim dfdy  As Double
  Dim j     As Integer
  Dim valid As Boolean
  Dim mol_frac(n_comps) As Double
  Dim HYZ As Double

' set function value to #VALUE error
  HallYarbGasZ = CVErr(xlErrValue)
 
' check input gravity/composition argument
' and get back gravity or array of composition
  Call GasPropCheckInput(Composition, mol_frac, valid)
  If Not valid Then Exit Function

' obtain critical properties
  Call CalculateCriticals(mol_frac, C7plusMolWt, C7plusDensGmCc, _
                          tcmv, pcmv, vcmv, amwv)
   ' obtain Z-Factor
 
  Call CalculateZFactor(ResTempF, PresPsia, tcmv, pcmv, HYZ)
  
  HallYarbGasZ = HYZ
  

  
   
End Function
'******************************************************************************

                      
Public Function WellHeadPsia(ByVal ResTempF As Double, ByVal PresPsia As Double, _
                             ByVal SurTempF As Double, ByVal TotVD As Double, _
                             ByVal Composition As Variant, _
                             ByVal C7plusMolWt As Double, _
                             ByVal C7plusDensGmCc As Double) As Variant
Attribute WellHeadPsia.VB_Description = "Calculate the pressure change with depth in a non flowing dry gas well."
Attribute WellHeadPsia.VB_ProcData.VB_Invoke_Func = " \n14"
                      
' Purpose:
'   Calculates Well Head Pressure for Static Dry Gas Well.  Well is divided into
'   ten intervals assuming a constant temperature gradient from surface to bottomhole

                      
 Dim tcmv  As Double, pcmv  As Double, vcmv As Double, amwv As Double
 
  Dim mol_frac(n_comps) As Double
  Dim valid As Boolean
  Dim HYZBh As Double
  Dim HYZWh As Double
  Dim Tavg As Double
  Dim Zavg As Double
  Dim T1 As Double
  Dim T2 As Double
  Dim p1 As Double
  Dim p2 As Double
  Dim DeltaX As Double
  Dim Tgradient As Double
  Dim pcalc As Double
  Dim j As Integer
  Dim k As Integer
  Dim nintervals As Integer
'
'   exit if depth step is 0
 If TotVD = 0 Then
  WellHeadPsia = PresPsia
  Exit Function
  End If
   
 
' set function value to #VALUE error
  WellHeadPsia = CVErr(xlErrValue)
  

' check input gravity/composition argument
' and get back gravity or array of composition
  Call GasPropCheckInput(Composition, mol_frac, valid)
  If Not valid Then Exit Function

' obtain critical properties
  Call CalculateCriticals(mol_frac, C7plusMolWt, C7plusDensGmCc, _
                          tcmv, pcmv, vcmv, amwv)
 ' Divide well into 10 intervals
 
 'nintervals = 10
 'DeltaX = TotVD / (nintervals)

 
 nintervals = TotVD / 100
  
 
 If nintervals < 1 Then nintervals = 1
 
 DeltaX = TotVD / nintervals
 
 
 T1 = ResTempF
 p1 = PresPsia
 Tgradient = (ResTempF - SurTempF) / TotVD
 Call CalculateZFactor(T1, p1, tcmv, pcmv, HYZBh)
 
 For k = 1 To nintervals
  
 p2 = 0.8 * p1
 T2 = T1 - Tgradient * DeltaX
 Tavg = (T2 + T1) / 2 + 459.67
 
 ' Iterate to solve for  Pressure in each interval
 
        For j = 1 To 10
 
        Call CalculateZFactor(T2, p2, tcmv, pcmv, HYZWh)
        Zavg = (HYZBh + HYZWh) / 2
   
        pcalc = p1 / Sqr(Exp(0.0375 * DeltaX * amwv / 28.96 / Tavg / Zavg))
 
        If Abs(p2 - pcalc) < 0.1 Then Exit For
        p2 = pcalc
        Next j
    
  p1 = p2
  T1 = T2
  HYZBh = HYZWh
  Next k
  
  WellHeadPsia = pcalc
  
 End Function

   

'******************************************************************************

  
 Sub CalculateZFactor(ByVal ResTempF As Double, _
                               ByVal PresPsia As Double, _
                               ByVal tcmv As Double, _
                               ByVal pcmv As Double, _
                               ByRef HYZ As Double)
Attribute CalculateZFactor.VB_Description = "Calculate gas volume factor in bbl/SCF from temperature, pressure, gas gravity, and Z factor"
Attribute CalculateZFactor.VB_ProcData.VB_Invoke_Func = " \n14"
            
  Dim rrt   As Double
  Dim ea    As Double
  Dim eb    As Double
  Dim ec    As Double
  Dim ed    As Double
  Dim ef    As Double
  Dim ey    As Double
  Dim rp    As Double
  Dim dfdy  As Double
  Dim j     As Integer
  
  rrt = tcmv / (ResTempF + 459.67)

  ea = 0.06125 * rrt * Exp(-1.2 * (1# - rrt) * (1# - rrt))
  eb = rrt * (14.76 - 9.76 * rrt + 4.58 * rrt * rrt)
  ec = rrt * (90.7 - 242.2 * rrt + 42.4 * rrt * rrt)
  ed = 1.18 + 2.82 * rrt
  ey = 0.001
  rp = PresPsia / pcmv
  
  For j = 1 To 60
  
    If (ey > 1#) Then ey = 0.9

    ef = -ea * rp / ey _
       + (1# + ey + ey * ey - (ey ^ 3)) _
       / ((1# - ey) ^ 3) - eb * ey + ec * (ey ^ ed)

    If Abs(ef) <= 0.000001 Then Exit For

    dfdy = ea * rp / (ey * ey) _
         + (4# + 4# * ey - 2# * ey * ey) _
         / ((1# - ey) ^ 4) - eb + ed * ec * (ey ^ (ed - 1#))

    ey = ey - ef / dfdy
    If (ey < 0#) Then ey = 0.000001
    
  Next j
 
  HYZ = ea * rp / ey
  
End Sub  ' CalculateZFactor

'**********************************************************************************


Public Function GasGravity(ByVal Composition As Variant, _
                           ByVal C7plusMolWt As Double) _
  As Variant
Attribute GasGravity.VB_Description = "Calculate Gas Gravity from Composition"
Attribute GasGravity.VB_ProcData.VB_Invoke_Func = " \n14"
                      
' Purpose:
'   Calculates Gas gravity
 
  Dim valid As Boolean
  Dim mol_frac(n_comps) As Double
  Dim mol_wt As Variant
  Dim mwm As Double
  Dim n As Integer

' set function value to #VALUE error
  GasGravity = CVErr(xlErrValue)

' check input composition argument and get back array of composition
  Call GasPropCheckInput(Composition, mol_frac, valid)
  If Not valid Then Exit Function
  
  mol_wt = Array(28.016, 16.042, 44.01, 30.068, 34.076, 44.094, _
                 58.12, 58.12, 72.146, 72.146, 86.172, C7plusMolWt)

' compute values for mixture
  mwm = 0
  For n = 1 To n_comps
    mwm = mwm + mol_frac(n) * mol_wt(n)
  Next n

  GasGravity = mwm / 28.96
  
End Function

'******************************************************************************
Public Function GasFVF(ByVal TempDegF As Double, _
                       ByVal PresPsia As Double, _
                       ByVal GasZ As Double) _
  As Double
Attribute GasFVF.VB_Description = "Calculate Gas Formation Volume Factor in bbl/SCF"
Attribute GasFVF.VB_ProcData.VB_Invoke_Func = " \n14"

' Purpose:
'   Calculates gas formation volume factor in bbl/SCF from gas Z,
'   pressure in psia, and temperature in deg F

 GasFVF = (5.03795 * (TempDegF + 459.67) * GasZ) / PresPsia


End Function

'******************************************************************************

Public Function ThodosGasVisc(ByVal TempDegF As Double, _
                              ByVal PresPsia As Double, _
                              ByVal Composition As Variant, _
                              ByVal C7plusMolWt As Double, _
                              ByVal C7plusDensGmCc As Double, _
                              ByVal GasZ As Double) _
  As Double
Attribute ThodosGasVisc.VB_Description = "Calculate gas viscosity in centipoise from temperature, pressure, gas gravity, and Z factor using the Thodos correlation"
Attribute ThodosGasVisc.VB_ProcData.VB_Invoke_Func = " \n14"

' Purpose:
'   Calculates gas viscosity in centipoise using the Thodos correlation from gas Z,
'   gas gravity, pressure in psia, and temperature in deg F

  Dim TdegR As Double
  Dim amwv  As Double
  Dim tcmv  As Double
  Dim pcmv  As Double
  Dim vcmv  As Double
  Dim rhorv As Double
  Dim chiv  As Double
  Dim trmv  As Double
  Dim stmuv As Double
  Dim mol_frac(n_comps) As Double
  Dim valid As Boolean

' check input gravity/composition argument
' and get back gravity or array of composition
  Call GasPropCheckInput(Composition, mol_frac, valid)
  If Not valid Then Exit Function

  TdegR = TempDegF + 459.67

' obtain critical properties
  Call CalculateCriticals(mol_frac, C7plusMolWt, C7plusDensGmCc, _
                          tcmv, pcmv, vcmv, amwv)

  rhorv = vcmv * PresPsia / (GasZ * 10.73 * TdegR)

  chiv = ((tcmv / 1.8) ^ (1# / 6#)) _
       / (Sqr(amwv) * ((pcmv / 14.696) ^ (2# / 3#)))

  trmv = TdegR / tcmv

  If trmv <= 1.5 Then
    stmuv = 0.00034 * (trmv ^ 0.888) / chiv
  Else
    stmuv = 0.001668 * ((0.1338 * trmv - 0.0932) ^ (5# / 9#)) / chiv
  End If

  ThodosGasVisc = rhorv * 0.0093324
  ThodosGasVisc = rhorv * (-0.040758 + ThodosGasVisc)
  ThodosGasVisc = rhorv * (0.058533 + ThodosGasVisc)
  ThodosGasVisc = 0.1023 + rhorv * (0.023364 + ThodosGasVisc)
  ThodosGasVisc = (ThodosGasVisc ^ 4#) - 0.0001
  ThodosGasVisc = (ThodosGasVisc / chiv) + stmuv

End Function

'----------------------------------------------------------------

Private Sub GasPropCheckInput(ByVal Composition As Variant, _
                              ByRef mol_frac() As Double, _
                              ByRef valid As Boolean)

'  checks Composition argument as valid range or array of mole fracs
'  or as single numeric value representing gas gravity

   Dim type_name As String
   Dim n As Integer
   Dim smf As Double

   valid = False
   
   type_name = TypeName(Composition)

'  check argument type and process accordingly
   If type_name = "Range" Then
      If Composition.Count <> n_comps Then
         MsgBox "Composition argument is not " & n_comps & " values"
         Exit Sub
      End If
      For n = 1 To n_comps
         If Not IsNumeric(Composition.Cells(n).Value) Then
            MsgBox "A composition value is not numeric"
            Exit Sub
         End If
         mol_frac(n) = Composition.Cells(n).Value
      Next n
   
   ElseIf type_name = "Variant()" Then
      If UBound(Composition) - LBound(Composition) + 1 <> n_comps Then
         MsgBox "Composition argument is not " & n_comps & " values"
         Exit Sub
      End If
      For n = 1 To n_comps
         If Not IsNumeric(Composition(n)) Then
            MsgBox "A composition value is not numeric"
            Exit Sub
         End If
         mol_frac(n) = Composition(n)
      Next n
   Else
      MsgBox "Composition argument is not a cell range or array"
      Exit Sub
   End If

'  check mole frac range and assign to array
   smf = 0
   For n = 1 To n_comps
      If mol_frac(n) < 0 Then
         MsgBox "A composition value is < 0"
         Exit Sub
      End If
      smf = smf + mol_frac(n)
   Next n
   If smf = 0 Then
      MsgBox "Composition sum is 0"
      Exit Sub
   End If
   For n = 1 To n_comps
      mol_frac(n) = mol_frac(n) / smf
   Next n

'  all OK
   valid = True

End Sub   ' GasPropCheckInput

'******************************************************************************

Private Sub CalculateCriticals(ByRef mol_frac() As Double, _
                               ByVal C7plusMolWt As Double, _
                               ByVal C7plusDensGmCc As Double, _
                               ByRef tcm As Double, _
                               ByRef pcm As Double, _
                               ByRef vcm As Double, _
                               ByRef mwm As Double)

' Purpose:
'   Calculate critical properties based on composition
'   including Wichert-Aziz adjustments for H2S and CO2 content
' Tc units are deg R, Pc units are psia
  
  Dim n As Integer
  Dim crit_tc As Variant, crit_pc As Variant, crit_vc As Variant
  Dim mol_wt As Variant
  Dim C7plusTC As Double, C7plusPC As Double, C7plusVC As Double
  Dim hyh As Double, hyo As Double, awa As Double, cor As Double
  Dim mwm2 As Double

' estimate C7+ criticals based on C7+ properties
  Call EstimatePseudoCriticals(C7plusMolWt, C7plusDensGmCc, _
                               C7plusTC, C7plusPC, C7plusVC)

' build arrays of criticals
  crit_tc = Array(227.29, 343.91, 547.49, 550.01, 672.39, 665.95, _
                  734.65, 765.31, 828.69, 845.19, 913.79, C7plusTC)
  crit_pc = Array(493#, 673.1, 1073#, 709.8, 1306#, 617.4, _
                  529.1, 550.7, 483#, 489.5, 440#, C7plusPC)
  crit_vc = Array(1.44, 1.59, 1.51, 2.37, 1.565, 3.21, _
                  4.21, 4.08, 4.9, 4.87, 5.93, C7plusVC)
  mol_wt = Array(28.016, 16.042, 44.01, 30.068, 34.076, 44.094, _
                 58.12, 58.12, 72.146, 72.146, 86.172, C7plusMolWt)

' compute values for mixture
  tcm = 0
  pcm = 0
  vcm = 0
  For n = 1 To n_comps
    tcm = tcm + mol_frac(n) * crit_tc(n)
    pcm = pcm + mol_frac(n) * crit_pc(n)
    vcm = vcm + mol_frac(n) * crit_vc(n)
    mwm = mwm + mol_frac(n) * mol_wt(n)
  Next n
  
' calculate Wichert-Aziz adjustment to Tc and Pc
  hyh = mol_frac(3)
  hyo = mol_frac(5)
  awa = hyh + hyo
  If awa > 0 Then
    cor = 120# * (awa ^ 0.9 - awa ^ 1.6) + 15# * (Sqr(hyo) - hyo ^ 4)
    pcm = pcm * (tcm - cor) / (tcm + hyo * (1# - hyo) * cor)
    tcm = tcm - cor
  End If

End Sub   ' CalculateCriticals

'------------------------------------------------------------------
  
Private Sub EstimatePseudoCriticals(ByVal PseudoMolWt As Double, _
                                    ByVal PseudoDensGmCC As Double, _
                                    ByRef PseudoTC As Double, _
                                    ByRef PseudoPC As Double, _
                                    ByRef PseudoVC As Double)

' Purpose:
'    Estimate critical properties for pseudocomponents using Erbar
'    (from Chao-Seader program) for Tc and Pc and Hall for Vc
   
   Dim smw As Double, ssg As Double
   Dim bp As Double, sx As Double
   Dim c1 As Double, sz As Double
   Dim b2 As Double, b3 As Double, qq As Double
   Dim sgrp As Double, sgrb As Double, sgrn As Double
   Dim xmp As Double, xmb As Double, xmn As Double
   Dim vfp As Double, vfb As Double, vfn As Double
   Dim wfp As Double, wfb As Double, wfn As Double
   Dim xfp As Double, xfb As Double, xfn As Double
   Dim xzu As Double, xzi As Double, xzo As Double

'  ESTIMATE TC AND PC FOR HYPOTHETICAL COMPONENT USING THE CORRELATIONS
'  BY JOHN ERBAR FROM HIS CHAO-SEADER PROGRAM
  If PseudoMolWt < 99# Then PseudoMolWt = 110#
   smw = PseudoMolWt
  If PseudoDensGmCC < 0.7 Then PseudoDensGmCC = 0.74
   ssg = PseudoDensGmCC / 0.999015
     
  
   bp = -264.65726 + (6.2374923 + (-0.021451518 + (0.000043992405 _
      - 0.0000000343845 * smw) * smw) * smw) * smw
   sx = 364.9632 + (-4.759161 + (0.04974927 + (-0.00015157213 _
      + 0.0000001431011 * smw) * smw) * smw) * smw
   bp = bp + sx * (ssg - 0.6)
   If ssg > 0.86 Then
      c1 = ssg - 0.86
      sz = ((16.823557 + (-0.071486 + 0.000998994 * smw) * smw) _
         + (65.42352 + (0.9092107 - 0.00801609 * smw) * smw) * c1) * c1
      bp = bp + Exp(sz)
   End If
   b2 = bp * bp
   b3 = b2 * bp
   sgrp = 0.57248636 + 0.0006948103 * bp - 0.00000075728178 * b2 _
        + 3.207736E-10 * b3
   sgrb = 0.91610329 - 0.00025041792 * bp + 0.00000035706705 * b2 _
        - 1.663182E-10 * b3
   sgrn = 1.9082378 - 0.0034097612 * bp + 0.0000043083811 * b2 _
        - 0.00000000185173 * b3
   xmp = 45.19165 + 0.26993166 * bp - 0.00008805269 * b2 _
       + 0.000000358456 * b3
   xmb = 14.93085 + 0.407469 * bp - 0.0004228928 * b2 _
       + 0.000000585848 * b3
   xmn = 4.825517 + 0.13158172 * bp + 0.00042669638 * b2 _
       - 0.000000149796 * b3
   If ssg <= sgrb Then
      vfp = (ssg - sgrb) / (sgrp - sgrb)
      vfb = 1# - vfp
      vfn = 0
   Else
      vfb = (ssg - sgrn) / (sgrb - sgrn)
      vfn = 1# - vfb
      vfp = 0
   End If
   qq = vfp * sgrp + vfb * sgrb + vfn * sgrn
   wfp = vfp * sgrp / qq
   wfb = vfb * sgrb / qq
   wfn = vfn * sgrn / qq
   qq = wfp / xmp + wfb / xmb + wfn / xmn
   xfp = wfp / (xmp * qq)
   xfb = wfb / (xmb * qq)
   xfn = wfn / (xmn * qq)
   xzu = 727.47745 + 1.2626579 * bp - 0.00045330572 * b2 _
       + 0.000000123217 * b3
   xzi = 839.54553 + 1.0776683 * bp - 0.00047253008 * b2 _
       + 0.00000028135443 * b3
   xzo = 1521.9287 - 1.5416102 * bp + 0.0033237804 * b2 _
       - 0.00000165984 * b3

   PseudoTC = xfp * xzu + xfb * xzi + xfn * xzo
   If PseudoTC < 0 Then PseudoTC = 0

   xzu = 593.11935 - 1.1655109 * bp + 0.001210827 * b2 _
       - 0.000000692878 * b3
   xzi = 1128.158 - 2.8264468 * bp + 0.0028014571 * b2 _
       - 0.000000972225 * b3
   xzo = 2748.4398 - 9.519013 * bp + 0.012696074 * b2 _
       - 0.00000597439 * b3

   PseudoPC = xfp * xzu + xfb * xzi + xfn * xzo
   If PseudoPC < 0 Then PseudoPC = 0

'  FOLLOWING VC CORRELATION BY K R HALL  1971
'  note use of specific gravity instead of density
   PseudoVC = 0.025 * (PseudoMolWt / (ssg ^ 0.69)) ^ 1.15

End Sub  ' EstimatePseudoCriticals