# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML labels işlemleri."""

from .Nodes import NodeHelper


class HTMLLabelsMixin:
    @staticmethod
    def _label_value_nodes(label_el):
        """Etiket satırını sonraki etikete, hücreye veya satır sonuna kadar okur."""
        curr = label_el.next
        while curr and curr.tag != "br":
            text = curr.select_text() or ""
            if curr.tag in ("dt", "th") or (curr.tag in ("span", "strong", "b", "label") and text.endswith(":")):
                break
            if curr.tag != "-comment":
                yield curr
            if curr.tag in ("div", "p", "ul", "ol") or (label_el.tag in ("td", "th", "dt") and curr.tag in ("td", "dd")):
                break
            curr = curr.next

    def meta_value(self, label: str, container_selector: str | None = None) -> str | None:
        """
        Herhangi bir container içinde: LABEL metnini içeren bir elementten SONRA gelen metni döndürür.
        label örn: "Oyuncular", "Yapım Yılı", "IMDB"
        """
        needle = label.casefold()

        # Belirli bir container varsa içinde ara, yoksa tüm dökümanda
        if container_selector:
            targets = self.select(container_selector)
        else:
            body    = self.parser.body
            targets = [NodeHelper(body)] if body else []

        for root in targets:
            if not root:
                continue

            # Label belirtebilecek elementleri tara
            for label_el in root.select("span, strong, b, label, dt, td, div.f-info-label, div.fi-label"):
                # tek .text() çağrısı + tek casefold — raw_txt orijinali, txt normalized
                raw_txt = label_el.select_text() or ""
                txt     = raw_txt.casefold()
                if needle not in txt:
                    continue

                # 1) Elementin kendi içindeki text'te LABEL: VALUE formatı olabilir
                # "Oyuncular: Brad Pitt" gibi. LABEL: sonrasını al.
                if ":" in raw_txt and needle in txt.split(":")[0]:  # txt zaten casefold
                    val = raw_txt.split(":", 1)[1].strip()
                    if val:
                        return val

                # İç içe metni kaybetmeden yalnız etiketin kendi satırını birleştir.
                parts = [text for node in self._label_value_nodes(label_el) if (text := node.select_text())]
                if value := " ".join(parts).strip(" :"):
                    return value

        return None

    def meta_list(self, label: str, container_selector: str | None = None, sep: str = ",") -> list[str]:
        """meta_value(...) çıktısını veya label'ın ebeveynindeki linkleri listeye döndürür."""
        needle = label.casefold()

        if container_selector:
            targets = self.select(container_selector)
        else:
            body    = self.parser.body
            targets = [NodeHelper(body)] if body else []

        for root in targets:
            if not root:
                continue
            for label_el in root.select("span, strong, b, label, dt, td, div.f-info-label, div.fi-label"):
                if needle in (label_el.select_text() or "").casefold():
                    # Aynı ebeveyndeki diğer metadata satırlarının linklerini alma.
                    links = label_el.select_texts("a")
                    for node in self._label_value_nodes(label_el):
                        if node.tag == "a":
                            if text := node.select_text():
                                links.append(text)
                        else:
                            links.extend(node.select_texts("a"))
                    if links:
                        return links

                    # Yoksa düz metin olarak meta_value mantığıyla al
                    raw = self.meta_value(label, container_selector=container_selector)
                    if not raw:
                        return []
                    return [x.strip() for x in raw.split(sep) if x.strip()]

        return []
