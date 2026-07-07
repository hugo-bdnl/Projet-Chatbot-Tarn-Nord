import { useState } from "react";
import { Plus, Search, Edit, Trash2, MapPin, Phone, Mail, Globe } from "lucide-react";

interface Organization {
  id: string;
  name: string;
  description: string;
  domain: string;
  address: string;
  city: string;
  postalCode: string;
  contactName: string;
  contactEmail: string;
  contactPhone: string;
  website: string;
}

const mockOrganizations: Organization[] = [
  {
    id: "1",
    name: "IMT Mines Albi",
    description: "École d'ingénieurs et centre de recherche",
    domain: "Recherche, Formation, Innovation",
    address: "Campus Jarlard, Route de Teillet",
    city: "Albi",
    postalCode: "81000",
    contactName: "Dr. Martin Dupont",
    contactEmail: "contact@imt-mines-albi.fr",
    contactPhone: "05 63 49 30 00",
    website: "www.imt-mines-albi.fr"
  },
  {
    id: "2",
    name: "AD'OCC",
    description: "Agence de développement économique d'Occitanie",
    domain: "Financement, Accompagnement",
    address: "27 Rue Maurice Fonvieille",
    city: "Toulouse",
    postalCode: "31000",
    contactName: "Sophie Martin",
    contactEmail: "contact@adocc.fr",
    contactPhone: "05 61 33 65 00",
    website: "www.adocc.fr"
  },
  {
    id: "3",
    name: "CRITT ICA",
    description: "Centre de Ressources Technologiques en Innovation",
    domain: "Innovation, Fabrication additive",
    address: "4 rue Firmin Oulès",
    city: "Albi",
    postalCode: "81000",
    contactName: "Jean Bernard",
    contactEmail: "contact@critt-ica.com",
    contactPhone: "05 63 47 25 10",
    website: "www.critt-ica.com"
  },
  {
    id: "4",
    name: "CNAM Formation Continue",
    description: "Centre de formation professionnelle",
    domain: "Formation, Compétences",
    address: "15 Avenue François Verdier",
    city: "Albi",
    postalCode: "81000",
    contactName: "Claire Rousseau",
    contactEmail: "albi@cnam-occitanie.fr",
    contactPhone: "05 63 43 15 00",
    website: "www.cnam-occitanie.fr"
  }
];

export function OrganizationManager() {
  const [organizations] = useState<Organization[]>(mockOrganizations);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);

  const filteredOrgs = organizations.filter(
    (org) =>
      org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      org.domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
      org.city.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex gap-4 items-center">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            placeholder="Rechercher une organisation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] transition-colors">
          <Plus size={20} />
          Ajouter une organisation
        </button>
      </div>

      {/* Organizations Grid */}
      <div className="grid md:grid-cols-2 gap-4">
        {filteredOrgs.map((org) => (
          <div
            key={org.id}
            className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => setSelectedOrg(org)}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="font-semibold text-lg text-slate-900 mb-1">{org.name}</h3>
                <p className="text-sm text-slate-600 mb-2">{org.description}</p>
                <span className="inline-block px-2 py-1 bg-[rgb(4,108,180)]/10 text-[rgb(4,108,180)] text-xs rounded">
                  {org.domain}
                </span>
              </div>
              <div className="flex gap-2">
                <button className="p-2 text-slate-600 hover:text-[rgb(4,108,180)] hover:bg-slate-100 rounded transition-colors">
                  <Edit size={18} />
                </button>
                <button className="p-2 text-slate-600 hover:text-red-600 hover:bg-slate-100 rounded transition-colors">
                  <Trash2 size={18} />
                </button>
              </div>
            </div>

            <div className="space-y-2 text-sm text-slate-600">
              <div className="flex items-center gap-2">
                <MapPin size={16} className="text-slate-400" />
                <span>{org.address}, {org.postalCode} {org.city}</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone size={16} className="text-slate-400" />
                <span>{org.contactPhone}</span>
              </div>
              <div className="flex items-center gap-2">
                <Mail size={16} className="text-slate-400" />
                <span>{org.contactEmail}</span>
              </div>
              <div className="flex items-center gap-2">
                <Globe size={16} className="text-slate-400" />
                <span>{org.website}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Organization Detail Modal */}
      {selectedOrg && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedOrg(null)}
        >
          <div
            className="bg-white rounded-xl max-w-2xl w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold text-slate-900 mb-4">{selectedOrg.name}</h2>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-700">Description</label>
                <p className="text-slate-600 mt-1">{selectedOrg.description}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700">Domaine d'activité</label>
                <p className="text-slate-600 mt-1">{selectedOrg.domain}</p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-slate-700">Contact</label>
                  <p className="text-slate-600 mt-1">{selectedOrg.contactName}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">Téléphone</label>
                  <p className="text-slate-600 mt-1">{selectedOrg.contactPhone}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">Email</label>
                  <p className="text-slate-600 mt-1">{selectedOrg.contactEmail}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">Site web</label>
                  <p className="text-slate-600 mt-1">{selectedOrg.website}</p>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700">Adresse</label>
                <p className="text-slate-600 mt-1">
                  {selectedOrg.address}<br />
                  {selectedOrg.postalCode} {selectedOrg.city}
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setSelectedOrg(null)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Fermer
              </button>
              <button className="px-4 py-2 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] transition-colors">
                Modifier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}