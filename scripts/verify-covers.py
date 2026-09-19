#!/usr/bin/env python3
"""Verifica covers do blog procurando imagens 'predominantemente vazias'.

Heurísticas aplicadas (uma imagem é reprovada se ATINGIR Pelo menos um critério):
  - Vazia por branco   : fração de pixels quase-brancos (luma > 245) > 60%
  - Vazia por escuro   : fração de pixels quase-pretos (luma < 10)   > 60%
  - Sem textura        : desvio padrão da luma < 12 E variedade de cor baixa
  - Poucas cores       : cores únicas (quantizadas a 5 bits) < 25 numa imagem >= 1200px
"""
import sys, glob, os
try:
    from PIL import Image
except ImportError:
    # Fallback para ambiente sem pip (VPS): Pillow extraído em /tmp/opencode/pillow
    sys.path.insert(0, '/tmp/opencode/pillow')
    from PIL import Image

THRESHOLDS = {
    'white_frac': 0.60,
    'black_frac': 0.60,
    'luma_std_min': 12.0,
    'unique_colors_min': 25,
}

def analyze(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    step = max(1, w // 300)  # amostra ~300 colunas p/ performance
    total = 0; white = 0; black = 0
    luma_sum = 0.0; luma_sq = 0.0
    colors = set()
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            luma = 0.299*r + 0.587*g + 0.114*b
            total += 1
            luma_sum += luma; luma_sq += luma*luma
            if luma > 245: white += 1
            elif luma < 10: black += 1
            colors.add((r >> 3, g >> 3, b >> 3))
    std = (luma_sq/total - (luma_sum/total)**2) ** 0.5
    return {
        'file': os.path.basename(path),
        'size': f'{w}x{h}',
        'white_frac': white/total,
        'black_frac': black/total,
        'luma_std': std,
        'unique_colors': len(colors),
        'mean_luma': luma_sum/total,
    }

def main():
    covers_dir = '/home/ubuntu/blog-content/posts/covers'
    files = sorted(glob.glob(os.path.join(covers_dir, '*.jpg')))
    print(f'Analisando {len(files)} covers...\n')
    print(f'{"ARQUIVO":<72} {"SIZE":<11} {"white%":>7} {"black%":>7} {"std":>6} {"cores":>6}  status')
    print('-' * 125)
    issues = 0
    for f in files:
        try:
            m = analyze(f)
        except Exception as e:
            print(f'ERRO {os.path.basename(f)}: {e}')
            continue
        flags = []
        if m['white_frac'] > THRESHOLDS['white_frac']:
            flags.append(f"BRANCO {m['white_frac']*100:.0f}%")
        if m['black_frac'] > THRESHOLDS['black_frac']:
            flags.append(f"PRETO {m['black_frac']*100:.0f}%")
        if m['luma_std'] < THRESHOLDS['luma_std_min']:
            flags.append(f"SEM-TEXTURA std={m['luma_std']:.1f}")
        if m['unique_colors'] < THRESHOLDS['unique_colors_min']:
            flags.append(f"POUCAS-CORES {m['unique_colors']}")
        status = '⚠️  ' + ' | '.join(flags) if flags else '✅ ok'
        if flags:
            issues += 1
        print(f"{m['file']:<72} {m['size']:<11} {m['white_frac']*100:>6.1f}% {m['black_frac']*100:>6.1f}% {m['luma_std']:>6.1f} {m['unique_colors']:>6d}  {status}")
    print(f'\nTotal: {len(files)} covers | Problemáticas: {issues}')

if __name__ == '__main__':
    main()