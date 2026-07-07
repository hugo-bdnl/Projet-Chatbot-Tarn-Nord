import { Link, useLocation } from "react-router";
import { Shield, Home } from "lucide-react";
import logoImg from "figma:asset/a937efa861fe9b8324613414aa95fd2ae6f2e0c0.png";

export function Header() {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith("/admin");

  return (
    <header className="bg-white shadow-sm border-b border-slate-200">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img src={logoImg} alt="Communauté d'Agglomération de l'Albigeois" className="h-12" />
          </Link>
          
          <nav className="flex items-center gap-4">
            {isAdmin ? (
              <Link
                to="/"
                className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-slate-900 transition-colors"
              >
                <Home size={20} />
                Accueil
              </Link>
            ) : (
              <Link
                to="/admin"
                className="flex items-center gap-2 px-4 py-2 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] transition-colors"
              >
                <Shield size={20} />
                Administration
              </Link>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}