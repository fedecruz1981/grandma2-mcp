"""
Extrae el texto del PDF de cues a un .txt plano, para poder leerlo.

No puedo leer PDFs ni imagenes directamente (este modelo no los acepta como
entrada), asi que los convierto a texto con PyMuPDF y leo el .txt.

Ademas saca las statistics de cada pagina para detectar de una vez si el PDF
tiene capa de texto o si es un escaneo (que necesitaria OCR).

Uso:
  python scripts/pdf_text.py <ruta.pdf> [salida.txt]
  python scripts/pdf_text.py <ruta.pdf> --probe    # solo diagnostico
"""
import sys
from pathlib import Path

import pymupdf


def probe(path):
    """Diagnostico: cuantas paginas, cuanto texto, es escaneo?"""
    doc = pymupdf.open(path)
    print(f"archivo   {path}")
    npages = doc.page_count
    print(f"paginas   {npages}")
    total = 0
    for i, page in enumerate(doc):
        t = page.get_text("text")
        total += len(t)
        imgs = page.get_images(full=True)
        head = " / ".join(t.split()[:12])
        print(f"  pag {i + 1:>3}  {len(t):>6} chars  {len(imgs)} img  "
              f"| {head[:70]}")
    doc.close()
    print(f"\ntotal {total} caracteres")
    if total < 50 * npages:
        print("VEREDICTO: casi sin texto -> probablemente escaneo. "
              "Hace falta OCR, decime y lo hacemos.")
    else:
        print("VEREDICTO: tiene capa de texto. Se puede parsear directo.")
    return total


def extract(path, out):
    doc = pymupdf.open(path)
    parts = []
    for i, page in enumerate(doc):
        parts.append(f"\n\n========== PAGINA {i + 1} ==========\n")
        parts.append(page.get_text("text"))
    text = "".join(parts)
    doc.close()
    out.write_text(text, encoding="utf-8")
    print(f"escrito {out}  ({out.stat().st_size // 1024} KB, "
          f"{len(text)} chars, {text.count(chr(10))} lineas)")
    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"no existe: {path}")
        sys.exit(1)
    if "--probe" in sys.argv:
        probe(path)
        return
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else path.with_suffix(".txt")
    extract(path, out)


if __name__ == "__main__":
    main()