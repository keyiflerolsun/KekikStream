# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML labels işlemleri."""

from .Nodes import NodeHelper


class HTMLLabelsMixin:
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
                raw_txt = label_el.text(strip=True) or ""
                txt     = raw_txt.casefold()
                if needle not in txt:
                    continue

                # 1) Elementin kendi içindeki text'te LABEL: VALUE formatı olabilir
                # "Oyuncular: Brad Pitt" gibi. LABEL: sonrasını al.
                if ":" in raw_txt and needle in txt.split(":")[0]:  # txt zaten casefold
                    val = raw_txt.split(":", 1)[1].strip()
                    if val:
                        return val

                # 2) Label sonrası gelen ilk text node'u veya element'i al
                curr = label_el.next
                while curr:
                    if curr.tag == "-text":
                        val = curr.text(strip=True).strip(" :")
                        if val:
                            return val
                    elif curr.tag != "br":
                        val = curr.text(strip=True).strip(" :")
                        if val:
                            return val
                    else:  # <br> gördüysek satır bitmiştir
                        break
                    curr = curr.next

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
                if needle in (label_el.text(strip=True) or "").casefold():
                    # Eğer elementin ebeveyninde linkler varsa (Kutucuklu yapı), onları al
                    parent = label_el.parent
                    links  = parent.select_texts("a") if parent else []
                    if links:
                        return links

                    # Yoksa düz metin olarak meta_value mantığıyla al
                    raw = self.meta_value(label, container_selector=container_selector)
                    if not raw:
                        return []
                    return [x.strip() for x in raw.split(sep) if x.strip()]

        return []
