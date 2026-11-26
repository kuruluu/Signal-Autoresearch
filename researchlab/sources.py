"""Attempt lawful public full-text access, retaining access failures explicitly."""
import concurrent.futures
import hashlib
import json
from urllib.request import Request, urlopen
from pypdf import PdfReader
from .catalog import RESEARCH

PUBLIC = {
 'P01':'https://pages.stern.nyu.edu/~lpederse/papers/TimeSeriesMomentum.pdf',
 'P03':'https://www.nber.org/system/files/working_papers/w2533/w2533.pdf',
 'P21':'https://www.nber.org/system/files/working_papers/w17653/w17653.pdf',
 'P24':'https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf',
 'P28':'https://repub.eur.nl/pub/10460/ERS-2007-044-F%26A.pdf',
 'P31':'https://www.nber.org/system/files/working_papers/w20071/w20071.pdf',
 'P35':'https://scholar.harvard.edu/files/kevin_pan/files/etfarbunderliqmismatch.pdf',
 'P37':'https://www.federalreserve.gov/econres/feds/files/2020097pap.pdf',
 'P41':'https://anderson-review.ucla.edu/wp-content/uploads/2021/03/Aboody-et-al_overnight_returns_and_firmspecific_investor_sentiment_JFQA2018.pdf',
 'P47':'https://www.federalreserve.gov/pubs/feds/2011/201152/201152pap.pdf',
 'P17':'https://www.mit.edu/~wangj/pap/CampbellGrossmanWang93.pdf',
 'P20':'https://depot.som.yale.edu/icf/papers/fileuploads/2694/original/2012_ICF_WPS_12-12_Ibbotson_Liquitiy_as_investment_style.pdf',
 'P36':'https://www.aeaweb.org/conference/2018/preliminary/paper/HGzHsdRe',
 'P39':'https://faculty.haas.berkeley.edu/hender/price_pressures.pdf',
 'P44':'https://academicweb.nd.edu/~zda/Google.pdf',
 'P04':'https://fac.comtech.depaul.edu/wdebondt/Publications/DoesStockM.pdf',
 'P05':'https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/8904.pdf',
 'P18':'https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf',
}


def fetch_paper(record):
    out = RESEARCH / 'fulltext'
    out.mkdir(exist_ok=True)
    pid = record['id']
    urls = [PUBLIC[pid]] if pid in PUBLIC else []
    if pid == 'P35':
        urls.append('https://www.esrb.europa.eu/pub/pdf/wp/esrb.wp59.en.pdf')
    if pid == 'P28':
        urls.append('https://repub.eur.nl/pub/10460/ERS-2007-044-F&A.pdf')
    urls += [l['URL'] for l in record['links'] if l.get('content-type') == 'application/pdf'][:1]
    if not urls:
        urls = [record['url']]
    attempts = []
    for url in dict.fromkeys(urls):
        try:
            pdf = out / f'{pid}.pdf'
            if not pdf.exists():
                with urlopen(Request(url, headers={'User-Agent': 'ETFResearchLab/0.1'}), timeout=12) as r:
                    body = r.read(20_000_000)
                if not body.startswith(b'%PDF'):
                    attempts.append({'url': url, 'result': 'Landing page/HTML; full text not retrieved'})
                    continue
                pdf.write_bytes(body)
            reader = PdfReader(pdf)
            text = '\n'.join(f'\n--- PAGE {i+1} ---\n' + (page.extract_text() or '') for i, page in enumerate(reader.pages))
            (out / f'{pid}.txt').write_text(text, encoding='utf-8')
            attempts.append({'url': url, 'result': 'PDF retrieved and text extracted'})
            return {'id': pid, 'full_text_accessible': True, 'pages': len(reader.pages),
                    'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    'version_note': 'Public copy may be working-paper version; compare with canonical publication.',
                    'attempts': attempts}
        except Exception as exc:
            attempts.append({'url': url, 'result': type(exc).__name__ + ': ' + str(exc)[:150]})
    return {'id': pid, 'full_text_accessible': False, 'attempts': attempts}


def main():
    records = json.loads((RESEARCH / 'catalog_metadata.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch_paper, records))
    (RESEARCH / 'fulltext_access.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    for r in results:
        print(r['id'], r['full_text_accessible'], flush=True)


if __name__ == '__main__':
    main()
