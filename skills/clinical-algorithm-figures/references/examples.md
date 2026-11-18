# Examples

Complete worked examples for both modes.

---

## Journal Mode — Primer Amenore

```python
#!/usr/bin/env python3
"""Şekil 1: Primer amenore tanısal yaklaşım algoritması (journal mode)"""

import graphviz

def create_algorithm():
    g = graphviz.Digraph(
        'primer_amenore',
        format='pdf',
        engine='dot',
        graph_attr={
            'rankdir': 'TB',
            'splines': 'ortho',
            'nodesep': '0.30',
            'ranksep': '0.40',
            'bgcolor': 'white',
            'fontname': 'Helvetica',
            'pad': '0.4',
            'dpi': '300',
            'margin': '0.15',
            'labelloc': 'b',
            'labeljust': 'l',
            'label': '\nŞekil 1.  Primer amenore tanısal yaklaşım algoritması.\n'
                     'FM: fizik muayene; USG: ultrasonografi; KAH: konjenital adrenal hiperplazi;\n'
                     'MRKH: Mayer-Rokitansky-Küster-Hauser sendromu; CAIS: komplet androjen duyarsızlık sendromu.',
            'fontsize': '10',
            'fontcolor': '#333333',
        },
        node_attr={
            'fontname': 'Helvetica',
            'fontsize': '11',
            'style': 'filled',
            'shape': 'box',
            'penwidth': '0.8',
            'color': '#333333',
            'margin': '0.14,0.07',
        },
        edge_attr={
            'fontname': 'Helvetica',
            'fontsize': '9',
            'color': '#333333',
            'penwidth': '0.8',
            'arrowsize': '0.6',
        }
    )

    # Journal palette
    WHITE  = 'white'
    LGRAY  = '#F2F2F2'
    ACC    = '#D6E4F0'
    ACC_DK = '#4472C4'
    BLK    = '#1A1A1A'
    DK     = '#333333'

    # L1 Title
    g.node('title',
           label='PRİMER AMENORE',
           fillcolor=ACC_DK, fontcolor='white',
           fontsize='14', fontname='Helvetica Bold',
           penwidth='0', margin='0.20,0.08')

    # L0 Criteria
    g.node('criteria',
           label=(
               '▪ 13 yaşına kadar meme gelişiminin başlamaması\n'
               '▪ Telarş evre ≥5 olan kişide 15 yaşına kadar menarş olmaması'
           ),
           fillcolor=WHITE, fontcolor=DK,
           fontsize='10', style='filled,dashed',
           margin='0.12,0.06')

    # L2 Workup
    g.node('workup',
           label='Anamnez + FM  |  USG  |  β-hCG, TSH, PRL, FSH',
           fillcolor=ACC, fontcolor=BLK,
           fontsize='11', margin='0.16,0.07')

    # L3 Branch
    g.node('uterus_var',
           label='UTERUS VAR',
           fillcolor=ACC_DK, fontcolor='white',
           fontsize='12', fontname='Helvetica Bold',
           penwidth='0', margin='0.18,0.07')

    g.node('uterus_yok',
           label='UTERUS YOK',
           fillcolor=ACC_DK, fontcolor='white',
           fontsize='12', fontname='Helvetica Bold',
           penwidth='0', margin='0.18,0.07')

    # L4 Lab
    g.node('fsh_high',
           label='FSH > 20 mIU/mL',
           fillcolor=ACC, fontcolor=BLK,
           fontsize='11')

    g.node('fsh_normal',
           label='FSH: Normal',
           fillcolor=ACC, fontcolor=BLK,
           fontsize='11')

    # L4 Action
    g.node('karyo_fsh',
           label='Karyotip iste\n17-hidroksilaz eksikliğini dışla',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='10')

    # L5 Results
    for nid, lab in [('k46xx', '46,XX'), ('k46xy', '46,XY'), ('k45x', '45,X')]:
        g.node(nid, label=lab,
               fillcolor=WHITE, fontcolor=BLK,
               fontsize='12', fontname='Helvetica Bold')

    # L6 Diagnoses
    g.node('dx_poy',
           label='Primer overyan yetmezlik\n17α-hidroksilaz eksikliği',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='10')

    g.node('dx_gonadal',
           label='Gonadal disgenezi\n17α-hidroksilaz eksikliği',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='10')

    g.node('dx_turner',
           label='Turner sendromu',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='10')

    # L6 DDX list
    g.node('fsh_n_ddx',
           label=(
               '▪ Anatomik anomaliler\n'
               '   (imperfore himen, transvers vajinal septum)\n'
               '▪ Sekonder amenore nedenleri\n'
               '   (hiperprolaktinemi, tiroid fonksiyon bozukluğu)\n'
               '▪ Konjenital GnRH eksikliği\n'
               '▪ Hipogonadotropik hipogonadizm\n'
               '▪ Sistemik hastalık'
           ),
           fillcolor=WHITE, fontcolor=DK,
           fontsize='10')

    # L4 Action (uterus yok path)
    g.node('karyo_uterus',
           label='Karyotip iste',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='12', fontname='Helvetica Bold')

    for nid, lab in [('u46xx', '46,XX'), ('u46xy', '46,XY')]:
        g.node(nid, label=lab,
               fillcolor=WHITE, fontcolor=BLK,
               fontsize='12', fontname='Helvetica Bold')

    g.node('dx_mullerian',
           label='Müllerian agenezi\n(MRKH sendromu)',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='10')

    g.node('dx_ais',
           label='Komplet androjen duyarsızlık\nsendromu (CAIS)\n5α-redüktaz eksikliği',
           fillcolor=LGRAY, fontcolor=DK,
           fontsize='10')

    # Edges
    g.edge('title', 'criteria', style='dashed', color='#999999', arrowhead='none')
    g.edge('criteria', 'workup')
    g.edge('workup', 'uterus_var')
    g.edge('workup', 'uterus_yok')
    g.edge('uterus_var', 'fsh_high')
    g.edge('uterus_var', 'fsh_normal')
    g.edge('fsh_high', 'karyo_fsh')
    g.edge('karyo_fsh', 'k46xx')
    g.edge('karyo_fsh', 'k46xy')
    g.edge('karyo_fsh', 'k45x')
    g.edge('k46xx', 'dx_poy')
    g.edge('k46xy', 'dx_gonadal')
    g.edge('k45x', 'dx_turner')
    g.edge('fsh_normal', 'fsh_n_ddx')
    g.edge('uterus_yok', 'karyo_uterus')
    g.edge('karyo_uterus', 'u46xx')
    g.edge('karyo_uterus', 'u46xy')
    g.edge('u46xx', 'dx_mullerian')
    g.edge('u46xy', 'dx_ais')

    return g

if __name__ == '__main__':
    g = create_algorithm()
    output = g.render('output/primer_amenore_journal', cleanup=True)
    print(f'Generated: {output}')
```

---

## Web Mode — Same Algorithm

Key differences from journal mode:
- `splines='line'` instead of `ortho`
- `style='filled,rounded'` on all nodes
- Blue gradient palette (B1–B9) instead of grayscale + accent
- Larger font sizes (title 17pt, branches 13pt)
- No figure caption
- `fontname='Helvetica Neue'`

```python
#!/usr/bin/env python3
"""Primer amenore (web mode)"""

import graphviz

def create_algorithm():
    g = graphviz.Digraph(
        'primer_amenore_web',
        format='pdf',
        engine='dot',
        graph_attr={
            'rankdir': 'TB',
            'splines': 'line',
            'nodesep': '0.35',
            'ranksep': '0.50',
            'bgcolor': 'white',
            'fontname': 'Helvetica Neue',
            'pad': '0.3',
            'dpi': '300',
            'margin': '0.2',
        },
        node_attr={
            'fontname': 'Helvetica Neue',
            'fontsize': '13',
            'style': 'filled,rounded',
            'shape': 'box',
            'penwidth': '0.6',
            'margin': '0.18,0.10',
        },
        edge_attr={
            'fontname': 'Helvetica Neue',
            'fontsize': '10',
            'color': '#6B7B8D',
            'penwidth': '1.0',
            'arrowsize': '0.7',
        }
    )

    # Web palette — blue gradient
    B1 = '#1B2A4A';  B2 = '#2C4A7C';  B3 = '#3D6098';  B4 = '#5A82B4'
    B5 = '#8AACC8';  B6 = '#B8D4E8';  B7 = '#D6E8F4';  B8 = '#EAF2F8'
    B9 = '#F4F8FC';  W  = 'white';    DK = '#1B2A4A';   MD = '#2C4A7C'

    # L1 Title
    g.node('title',
           label='PRİMER AMENORE',
           fillcolor=B1, fontcolor=W,
           fontsize='17', fontname='Helvetica Neue Bold',
           penwidth='0', margin='0.25,0.12')

    # L0 Criteria
    g.node('criteria',
           label=(
               '▪ 13 yaşına kadar meme gelişiminin başlamaması\n'
               '▪ Telarş evre ≥5 olan kişide 15 yaşına kadar menarş olmaması'
           ),
           fillcolor=B9, fontcolor=DK,
           fontsize='11', style='filled,rounded,dashed',
           penwidth='0.8', color=B5,
           margin='0.18,0.08')

    # L2 Workup
    g.node('workup',
           label='Anamnez + FM  |  USG  |  β-hCG, TSH, PRL, FSH',
           fillcolor=B3, fontcolor=W,
           fontsize='14', penwidth='0',
           margin='0.22,0.10')

    # L3 Branch
    g.node('uterus_var',
           label='UTERUS VAR',
           fillcolor=B4, fontcolor=W,
           fontsize='13', fontname='Helvetica Neue Bold',
           penwidth='0', margin='0.20,0.08')

    g.node('uterus_yok',
           label='UTERUS YOK',
           fillcolor=B4, fontcolor=W,
           fontsize='13', fontname='Helvetica Neue Bold',
           penwidth='0', margin='0.20,0.08')

    # ... remaining nodes follow same pattern with B5-B8 fills ...
    # See design-spec.md for the full level-to-color mapping

    return g

if __name__ == '__main__':
    g = create_algorithm()
    output = g.render('output/primer_amenore_web', cleanup=True)
    print(f'Generated: {output}')
```

---

## Quick Reference: Mode Differences

| Property | Journal | Web |
|----------|---------|-----|
| Corners | Sharp 90° | Rounded |
| Edges | Orthogonal (`ortho`) | Straight (`line`) |
| Font | Helvetica | Helvetica Neue |
| Title size | 14pt | 17pt |
| Palette | White + gray + 1 accent blue | 9-stop blue gradient |
| Caption | Yes (bottom, with abbreviations) | No |
| Criteria border | Dashed | Dashed + rounded |
| Branch headers | `ACC_DK` (#4472C4) white text | `B4` (#5A82B4) white text |
| Diagnosis fills | `LGRAY` (#F2F2F2) | `B8` (#EAF2F8) |
