# Third-party Web Assets

DealHunter serves its Web UI without runtime CDNs. The following upstream assets
are vendored under `src/dealhunter/web/static/`; changing any of them requires an
explicit version/hash update and the normal test gate.

| Asset | Vendored files | Version | Upstream | License | SHA-256 |
|---|---|---:|---|---|---|
| Bootstrap | `css/bootstrap.min.css` | 5.3.3 | https://getbootstrap.com/ / https://github.com/twbs/bootstrap | MIT | `3c8f27e6009ccfd710a905e6dcf12d0ee3c6f2ac7da05b0572d3e0d12e736fc8` |
| Bootstrap bundle | `js/bootstrap.bundle.min.js` | 5.3.3 | https://getbootstrap.com/ / https://github.com/twbs/bootstrap | MIT | `0833b2e9c3a26c258476c46266e6877fc75218625162e0460be9a3a098a61c6c` |
| htmx | `js/htmx.min.js` | 1.9.12 | https://v1.htmx.org/ / https://github.com/bigskysoftware/htmx | 0BSD | `449317ade7881e949510db614991e195c3a099c4c791c24dacec55f9f4a2a452` |
| Chart.js | `js/chart.umd.min.js` | 4.4.2 | https://www.chartjs.org/ / https://github.com/chartjs/Chart.js | MIT | `08dfa4730571b23810c34fc39c5101461ecafca56c3f92caf4850509cb158f30` |

The Bootstrap JavaScript file is the upstream **bundle** build and therefore
contains Bootstrap's bundled positioning dependency. DealHunter does not ship a
separate Popper file or maintain a separate Popper version contract.

The original repository commits that introduced these files did not record a
separate download manifest. The table therefore records the upstream project
identity/version embedded in the vendored artifacts plus the exact repository
hashes, which are the reproducible authority for the bytes DealHunter serves.
