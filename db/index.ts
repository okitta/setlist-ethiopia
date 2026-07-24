function required(name: string) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not configured.`);
  return value;
}

export function getSupabaseAdminHeaders() {
  const serviceRoleKey = required("SUPABASE_SERVICE_ROLE_KEY");
  return {
    apikey: serviceRoleKey,
    Authorization: `Bearer ${serviceRoleKey}`,
    "Content-Type": "application/json",
    Prefer: "return=representation",
  };
}

export function getSupabaseRestUrl(path: string) {
  return `${required("NEXT_PUBLIC_SUPABASE_URL")}/rest/v1/${path}`;
}
