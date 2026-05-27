-- AgentDB — allow authenticated (anon key) reads on active knowledge items
-- Run in Supabase: Dashboard → SQL Editor → paste and run

-- Allow SELECT for the anon role (covers requests made with the publishable key)
CREATE POLICY "anon read active knowledge"
  ON knowledge
  FOR SELECT
  TO anon
  USING (is_active = TRUE);
