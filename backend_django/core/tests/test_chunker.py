from django.test import SimpleTestCase

from core.ingestion.chunker import trocear_documento


class ChunkerTests(SimpleTestCase):
    def test_ningun_fragmento_cruza_una_pagina(self):
        paginas = [f"Contenido de la pagina {i}. " * 80 for i in range(1, 6)]
        fragmentos = trocear_documento(paginas, tam=300, solape=50)

        self.assertTrue(fragmentos)
        for f in fragmentos:
            self.assertEqual(f.page_start, f.page_end)

    def test_las_paginas_se_numeran_desde_uno(self):
        fragmentos = trocear_documento(["primera", "segunda"], tam=900, solape=100)
        self.assertEqual([f.page_start for f in fragmentos], [1, 2])

    def test_los_ordinales_son_consecutivos_y_globales(self):
        paginas = ["texto largo " * 60, "otro texto largo " * 60]
        fragmentos = trocear_documento(paginas, tam=200, solape=40)
        self.assertEqual([f.ordinal for f in fragmentos], list(range(len(fragmentos))))

    def test_se_ignoran_las_paginas_vacias(self):
        fragmentos = trocear_documento(["", "   ", "con contenido"], tam=900, solape=100)
        self.assertEqual(len(fragmentos), 1)
        self.assertEqual(fragmentos[0].page_start, 3)

    def test_un_parrafo_mas_largo_que_la_ventana_se_parte(self):
        fragmentos = trocear_documento(["x" * 5000], tam=500, solape=50)
        self.assertGreater(len(fragmentos), 1)
        self.assertTrue(all(len(f.text) <= 900 for f in fragmentos))
