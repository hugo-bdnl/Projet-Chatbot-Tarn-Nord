import { useCallback, useEffect, useState } from "react";
import { Plus, Search, Edit, Trash2, MapPin, Phone, Mail, Globe, AlertCircle, X } from "lucide-react";
import {
  listOrganizations, listDomains, createOrganization, updateOrganization, deleteOrganization,
  errorMessage, type Organization, type OrganizationInput, type Domain, type Site, type Contact,
} from "../../lib/api";

const EMPTY_SITE: Site = { label: "", address: "", postal_code: "", city: "" };
const EMPTY_CONTACT: Contact = { last_name: "", first_name: "", role: "", email: "", phone: "" };

const EMPTY_FORM: OrganizationInput = {
  name: "",
  description: "",
  website: "",
  keywords: [],
  domains: [],
  sites: [{ ...EMPTY_SITE }],
  contacts: [{ ...EMPTY_CONTACT }],
  active: true,
};

function toForm(org: Organization): OrganizationInput {
  return {
    name: org.name,
    description: org.description,
    website: org.website,
    keywords: [...org.keywords],
    domains: [...org.domains],
    sites: org.sites.length > 0 ? org.sites.map((s) => ({ ...s })) : [{ ...EMPTY_SITE }],
    contacts: org.contacts.length > 0 ? org.contacts.map((c) => ({ ...c })) : [{ ...EMPTY_CONTACT }],
    active: org.active,
  };
}

/** Une ligne de site ou de contact entierement vide n'est pas envoyee au serveur. */
function clean(payload: OrganizationInput): OrganizationInput {
  const filled = (values: string[]) => values.some((v) => v.trim() !== "");
  return {
    ...payload,
    sites: payload.sites.filter((s) => filled([s.label, s.address, s.postal_code, s.city])),
    contacts: payload.contacts.filter((c) => filled([c.last_name, c.first_name, c.role, c.email, c.phone])),
  };
}

export function OrganizationManager() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [domainFilter, setDomainFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ org: Organization | null; form: OrganizationInput } | null>(null);
  const [deleting, setDeleting] = useState<Organization | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    listOrganizations({ q: searchQuery || undefined, domain: domainFilter || undefined, limit: 500 })
      .then((result) => {
        setOrganizations(result.items);
        setTotal(result.total);
        setError(null);
      })
      .catch((err) => {
        setOrganizations([]);
        setError(errorMessage(err));
      })
      .finally(() => setLoading(false));
  }, [searchQuery, domainFilter]);

  // La recherche part vers le serveur (parametre `q`), avec une courte temporisation
  // pour ne pas envoyer une requete par frappe.
  useEffect(() => {
    const timer = window.setTimeout(load, searchQuery ? 300 : 0);
    return () => window.clearTimeout(timer);
  }, [load, searchQuery]);

  useEffect(() => {
    listDomains().then(setDomains).catch(() => setDomains([]));
  }, []);

  const handleSaved = () => {
    setEditing(null);
    load();
    listDomains().then(setDomains).catch(() => undefined);
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await deleteOrganization(deleting.id);
      setDeleting(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[240px] relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            placeholder="Rechercher une organisation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
          />
        </div>
        <select
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]"
        >
          <option value="">Tous les domaines</option>
          {domains.map((domain) => (
            <option key={domain.id} value={domain.name}>
              {domain.name} ({domain.organizations})
            </option>
          ))}
        </select>
        <button
          onClick={() => setEditing({ org: null, form: { ...EMPTY_FORM } })}
          className="flex items-center gap-2 px-4 py-2 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] transition-colors"
        >
          <Plus size={20} />
          Ajouter une organisation
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Annuaire indisponible</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {!error && (
        <p className="text-sm text-slate-600">
          {loading ? "Chargement..." : `${organizations.length} organisation(s) affichee(s) sur ${total}`}
        </p>
      )}

      {/* Organizations Grid */}
      <div className="grid md:grid-cols-2 gap-4">
        {organizations.map((org) => {
          const site = org.sites[0];
          const contact = org.contacts[0];
          return (
            <div
              key={org.id}
              className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-lg text-slate-900">{org.name}</h3>
                    {!org.active && (
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">inactive</span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 mb-2 line-clamp-2">{org.description}</p>
                  <div className="flex flex-wrap gap-1">
                    {org.domains.map((domain) => (
                      <span
                        key={domain}
                        className="inline-block px-2 py-1 bg-[rgb(4,108,180)]/10 text-[rgb(4,108,180)] text-xs rounded"
                      >
                        {domain}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    aria-label={`Modifier ${org.name}`}
                    onClick={() => setEditing({ org, form: toForm(org) })}
                    className="p-2 text-slate-600 hover:text-[rgb(4,108,180)] hover:bg-slate-100 rounded transition-colors"
                  >
                    <Edit size={18} />
                  </button>
                  <button
                    aria-label={`Supprimer ${org.name}`}
                    onClick={() => setDeleting(org)}
                    className="p-2 text-slate-600 hover:text-red-600 hover:bg-slate-100 rounded transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>

              <div className="space-y-2 text-sm text-slate-600">
                {site && (site.address || site.city) && (
                  <div className="flex items-center gap-2">
                    <MapPin size={16} className="text-slate-400" />
                    <span>
                      {[site.address, [site.postal_code, site.city].filter(Boolean).join(" ")]
                        .filter(Boolean)
                        .join(", ")}
                    </span>
                  </div>
                )}
                {contact?.phone && (
                  <div className="flex items-center gap-2">
                    <Phone size={16} className="text-slate-400" />
                    <span>{contact.phone}</span>
                  </div>
                )}
                {contact?.email && (
                  <div className="flex items-center gap-2">
                    <Mail size={16} className="text-slate-400" />
                    <span>{contact.email}</span>
                  </div>
                )}
                {org.website && (
                  <div className="flex items-center gap-2">
                    <Globe size={16} className="text-slate-400" />
                    <span>{org.website.replace(/^https?:\/\//, "")}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!loading && !error && organizations.length === 0 && (
        <p className="text-slate-600">Aucune organisation ne correspond a cette recherche.</p>
      )}

      {editing && (
        <OrganizationForm
          organization={editing.org}
          initial={editing.form}
          domains={domains}
          onClose={() => setEditing(null)}
          onSaved={handleSaved}
        />
      )}

      {deleting && (
        <ConfirmDelete
          organization={deleting}
          onCancel={() => setDeleting(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}

function OrganizationForm({
  organization, initial, domains, onClose, onSaved,
}: {
  organization: Organization | null;
  initial: OrganizationInput;
  domains: Domain[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<OrganizationInput>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Partial<OrganizationInput>) => setForm((prev) => ({ ...prev, ...patch }));

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setError("Le nom est obligatoire.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = clean(form);
      if (organization) {
        await updateOrganization(organization.id, payload);
      } else {
        await createOrganization(payload);
      }
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div
        className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-2xl font-bold text-slate-900">
            {organization ? organization.name : "Nouvelle organisation"}
          </h2>
          <button onClick={onClose} className="p-1 text-slate-500 hover:text-slate-900" aria-label="Fermer">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          <Field label="Nom">
            <input
              type="text"
              value={form.name}
              onChange={(e) => update({ name: e.target.value })}
              className={inputClass}
            />
          </Field>

          <Field
            label="Description"
            hint="C'est ce texte qui est indexe pour la recherche : le rediger avec les mots des industriels ameliore directement l'orientation."
          >
            <textarea
              rows={4}
              value={form.description}
              onChange={(e) => update({ description: e.target.value })}
              className={inputClass}
            />
          </Field>

          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Site web">
              <input
                type="text"
                value={form.website}
                onChange={(e) => update({ website: e.target.value })}
                className={inputClass}
              />
            </Field>
            <Field label="Domaines d'activite" hint="Separes par des virgules">
              <input
                type="text"
                list="domain-options"
                value={form.domains.join(", ")}
                onChange={(e) =>
                  update({ domains: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })
                }
                className={inputClass}
              />
              <datalist id="domain-options">
                {domains.map((domain) => (
                  <option key={domain.id} value={domain.name} />
                ))}
              </datalist>
            </Field>
          </div>

          <Field label="Mots-cles" hint="Acronymes et synonymes, separes par des virgules">
            <input
              type="text"
              value={form.keywords.join(", ")}
              onChange={(e) =>
                update({ keywords: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })
              }
              className={inputClass}
            />
          </Field>

          <ListEditor
            title="Sites"
            addLabel="Ajouter un site"
            items={form.sites}
            onAdd={() => update({ sites: [...form.sites, { ...EMPTY_SITE }] })}
            onRemove={(index) => update({ sites: form.sites.filter((_, i) => i !== index) })}
            render={(site, index) => (
              <div className="grid md:grid-cols-2 gap-3">
                <input
                  type="text" placeholder="Libelle (siege, antenne...)" value={site.label}
                  onChange={(e) => {
                    const sites = [...form.sites];
                    sites[index] = { ...site, label: e.target.value };
                    update({ sites });
                  }}
                  className={inputClass}
                />
                <input
                  type="text" placeholder="Adresse" value={site.address}
                  onChange={(e) => {
                    const sites = [...form.sites];
                    sites[index] = { ...site, address: e.target.value };
                    update({ sites });
                  }}
                  className={inputClass}
                />
                <input
                  type="text" placeholder="Code postal" value={site.postal_code}
                  onChange={(e) => {
                    const sites = [...form.sites];
                    sites[index] = { ...site, postal_code: e.target.value };
                    update({ sites });
                  }}
                  className={inputClass}
                />
                <input
                  type="text" placeholder="Ville" value={site.city}
                  onChange={(e) => {
                    const sites = [...form.sites];
                    sites[index] = { ...site, city: e.target.value };
                    update({ sites });
                  }}
                  className={inputClass}
                />
              </div>
            )}
          />

          <ListEditor
            title="Contacts"
            addLabel="Ajouter un contact"
            items={form.contacts}
            onAdd={() => update({ contacts: [...form.contacts, { ...EMPTY_CONTACT }] })}
            onRemove={(index) => update({ contacts: form.contacts.filter((_, i) => i !== index) })}
            render={(contact, index) => (
              <div className="grid md:grid-cols-2 gap-3">
                <input
                  type="text" placeholder="Prenom" value={contact.first_name}
                  onChange={(e) => {
                    const contacts = [...form.contacts];
                    contacts[index] = { ...contact, first_name: e.target.value };
                    update({ contacts });
                  }}
                  className={inputClass}
                />
                <input
                  type="text" placeholder="Nom" value={contact.last_name}
                  onChange={(e) => {
                    const contacts = [...form.contacts];
                    contacts[index] = { ...contact, last_name: e.target.value };
                    update({ contacts });
                  }}
                  className={inputClass}
                />
                <input
                  type="text" placeholder="Fonction ou service" value={contact.role}
                  onChange={(e) => {
                    const contacts = [...form.contacts];
                    contacts[index] = { ...contact, role: e.target.value };
                    update({ contacts });
                  }}
                  className={inputClass}
                />
                <input
                  type="text" placeholder="Telephone" value={contact.phone}
                  onChange={(e) => {
                    const contacts = [...form.contacts];
                    contacts[index] = { ...contact, phone: e.target.value };
                    update({ contacts });
                  }}
                  className={inputClass}
                />
                <input
                  type="email" placeholder="Courriel" value={contact.email}
                  onChange={(e) => {
                    const contacts = [...form.contacts];
                    contacts[index] = { ...contact, email: e.target.value };
                    update({ contacts });
                  }}
                  className={`${inputClass} md:col-span-2`}
                />
              </div>
            )}
          />

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => update({ active: e.target.checked })}
              className="h-4 w-4"
            />
            <span className="text-sm text-slate-700">
              Active — une organisation inactive reste en base mais n'est plus proposee par le chatbot
            </span>
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <p className="text-xs text-slate-500">
            L'enregistrement met l'index de recherche a jour immediatement (reindexation incrementale).
          </p>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 bg-[rgb(4,108,180)] text-white rounded-lg hover:bg-[rgb(4,90,150)] disabled:bg-slate-300 transition-colors"
          >
            {saving ? "Enregistrement..." : "Enregistrer"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ConfirmDelete({
  organization, onCancel, onConfirm,
}: {
  organization: Organization;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={onCancel}>
      <div className="bg-white rounded-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Supprimer cette organisation ?</h2>
        <p className="text-slate-600">
          « {organization.name} » sera retiree de l'annuaire et de l'index de recherche. Pour la masquer
          sans perdre ses donnees, decochez plutot « Active » dans la fiche.
        </p>
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Supprimer
          </button>
        </div>
      </div>
    </div>
  );
}

const inputClass =
  "w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[rgb(4,108,180)]";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-2">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

function ListEditor<T>({
  title, addLabel, items, onAdd, onRemove, render,
}: {
  title: string;
  addLabel: string;
  items: T[];
  onAdd: () => void;
  onRemove: (index: number) => void;
  render: (item: T, index: number) => React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-700">{title}</span>
        <button onClick={onAdd} className="text-sm text-[rgb(4,108,180)] hover:underline">
          {addLabel}
        </button>
      </div>
      <div className="space-y-3">
        {items.map((item, index) => (
          <div key={index} className="rounded-lg border border-slate-200 p-3">
            <div className="flex justify-end">
              <button
                onClick={() => onRemove(index)}
                className="text-xs text-slate-500 hover:text-red-600"
                aria-label={`Retirer ${title} ${index + 1}`}
              >
                Retirer
              </button>
            </div>
            {render(item, index)}
          </div>
        ))}
      </div>
    </div>
  );
}
