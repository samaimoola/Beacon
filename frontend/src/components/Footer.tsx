import { Logo } from '@/components/Nav';

export default function Footer() {
  return (
    <footer className="footer on-dark">
      <div className="container-wide grid gap-10 py-14 md:grid-cols-[1fr_1.4fr]">
        <div>
          <div className="flex items-center gap-2.5">
            <Logo className="h-9 w-9" />
            <span className="font-display text-2xl text-ivory">Beacon</span>
          </div>
          <p className="mt-3 font-display text-lg italic text-mist/80">When the lights go out, your plan doesn't</p>
          <p className="mt-6 max-w-sm text-xs leading-relaxed text-ivory/60">
            Beacon is a student prototype built for AEP&apos;s HackOHI/O 2026 challenge and is not affiliated with
            AEP. Storms, damage presets, crews, and notices shown are simulated. The illustration is original artwork
            and is not a map, live weather, or outage status.
          </p>
        </div>
        <div>
          <h2 className="eyebrow text-mist">Confirmed information</h2>
          <p className="mt-1 text-xs text-ivory/55">Verified facts with sources — not scenario estimates.</p>
          <ul className="mt-4 space-y-3 text-sm leading-relaxed">
            <li>
              <strong className="text-ivory">Report an AEP Ohio outage:</strong> call{' '}
              <a href="tel:1-800-672-2231">1-800-672-2231</a> (
              <a href="https://www.aepohio.com/outages/" target="_blank" rel="noopener noreferrer">
                AEP Ohio outages
              </a>
              ).
            </li>
            <li>
              <strong className="text-ivory">Live outage map:</strong>{' '}
              <a href="https://outagemap.aepohio.com/" target="_blank" rel="noopener noreferrer">
                AEP Ohio outage map
              </a>
              .
            </li>
            <li>
              <strong className="text-ivory">Medical needs &amp; disconnection:</strong> In Ohio, a medical certificate can
              help prevent a disconnection for nonpayment; it does not guarantee restoration priority during storm outages (
              <a href="https://puco.ohio.gov/utilities/electricity/resources/utility-assistance-programs" target="_blank" rel="noopener noreferrer">
                PUCO
              </a>
              ,{' '}
              <a href="https://occ.ohio.gov/factsheet/30-day-medical-certificate" target="_blank" rel="noopener noreferrer">
                OCC
              </a>
              ).
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
