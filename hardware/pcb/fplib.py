"""Custom footprints for the collar boards, built with the pcbnew API."""
import pcbnew
MM = pcbnew.FromMM

def _pad(fp, num, x, y, w, h, shape=pcbnew.PAD_SHAPE_ROUNDRECT, smd=True, drill=0.0, layer_bottom=False, paste=True):
    p = pcbnew.PAD(fp)
    p.SetNumber(str(num))
    p.SetShape(shape)
    if smd:
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        ls = pcbnew.LSET()
        if layer_bottom:
            ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask); ls.AddLayer(pcbnew.B_Paste)
        else:
            ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
            if paste: ls.AddLayer(pcbnew.F_Paste)
        p.SetLayerSet(ls)
    else:
        p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        p.SetLayerSet(pcbnew.PAD.PTHMask())
        p.SetDrillSize(pcbnew.VECTOR2I(MM(drill), MM(drill)))
    p.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
    if shape == pcbnew.PAD_SHAPE_ROUNDRECT:
        p.SetRoundRectRadiusRatio(0.25)
    p.SetPos0(pcbnew.VECTOR2I(MM(x), MM(y)))
    p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    fp.Add(p)
    return p

def _line(fp, layer, x1, y1, x2, y2, w=0.12):
    s = pcbnew.FP_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(layer); s.SetWidth(MM(w))
    s.SetStart0(pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd0(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    s.SetDrawCoord()
    fp.Add(s)

def mk24(board):
    """Standex-Meder MK24, lead design 2 (flat bent SMD leads). Body 5.0 x 2.2 mm,
    5.5 mm over the leads (series datasheet, 2019). Pads extend 0.45 mm beyond
    the lead ends and 0.5 mm under the body. VERIFY against the product
    drawing before ordering."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("collar", "Reed_MK24_LeadDesign2"))
    _pad(fp, 1, -2.6, 0, 1.2, 1.4)
    _pad(fp, 2, 2.6, 0, 1.2, 1.4)
    for (x1, y1, x2, y2) in ((-1.8, -1.2, 1.8, -1.2), (-1.8, 1.2, 1.8, 1.2)):
        _line(fp, pcbnew.F_SilkS, x1, y1, x2, y2)
    for (x1, y1, x2, y2) in ((-3.4, -1.35, 3.4, -1.35), (3.4, -1.35, 3.4, 1.35), (3.4, 1.35, -3.4, 1.35), (-3.4, 1.35, -3.4, -1.35)):
        _line(fp, pcbnew.F_CrtYd, x1, y1, x2, y2, 0.05)
    for (x1, y1, x2, y2) in ((-2.5, -1.1, 2.5, -1.1), (2.5, -1.1, 2.5, 1.1), (2.5, 1.1, -2.5, 1.1), (-2.5, 1.1, -2.5, -1.1)):
        _line(fp, pcbnew.F_Fab, x1, y1, x2, y2, 0.1)
    return fp

def batt_neg(board):
    """Centre negative pin, as on the Deben: plated hole for a 1.0 mm pin that
    stands the board off the top cell and presses on its negative cap."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("collar", "Batt_Neg_CentrePin_D1.0"))
    _pad(fp, 1, 0, 0, 2.0, 2.0, shape=pcbnew.PAD_SHAPE_CIRCLE, smd=False, drill=1.0)
    return fp

def batt_pos(board):
    """Side positive pin: plated hole for a 1.0 mm pin, soldered and bent down
    the side of the cell stack."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("collar", "Batt_Pos_SidePin_D1.0"))
    _pad(fp, 1, 0, 0, 2.0, 2.0, shape=pcbnew.PAD_SHAPE_CIRCLE, smd=False, drill=1.0)
    return fp

def coil_pad(board):
    """Plated hole for the coil's magnet wire."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("collar", "Coil_Wire_D0.7"))
    _pad(fp, 1, 0, 0, 1.5, 1.5, shape=pcbnew.PAD_SHAPE_CIRCLE, smd=False, drill=0.7)
    return fp

def isp_pad(board):
    """Pogo-pin landing for in-circuit programming. No paste: stays flat."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("collar", "ISP_Pad_D1.0"))
    _pad(fp, 1, 0, 0, 1.0, 1.0, shape=pcbnew.PAD_SHAPE_CIRCLE, paste=False)
    return fp
