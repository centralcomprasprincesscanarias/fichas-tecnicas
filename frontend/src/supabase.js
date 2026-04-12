import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://ifiwuloipapsezmssyda.supabase.co'
const supabaseAnonKey = 'sb_publishable_ikJ6Zdz4AKjH7vy3bo29kw_ih7ylCci'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)