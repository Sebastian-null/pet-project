import "./styles.css";
import "./overrides.css";
import { CartProvider } from "./cart";
import { SiteChrome } from "./ui";
export const metadata = { title: "Briefs — underwear for every day", description: "Thoughtfully made underwear for him and her" };
export default function Layout({ children }: { children: React.ReactNode }) { return <html lang="uk"><body><CartProvider><SiteChrome />{children}<footer>BRIEFS · Everyday comfort, thoughtfully made</footer></CartProvider></body></html>; }
