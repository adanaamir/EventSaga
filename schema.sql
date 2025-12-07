CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'attendee' CHECK (role IN ('attendee', 'organizer')),
    avatar_url TEXT,
    bio TEXT,
    location TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- Trigger to auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organizer_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    datetime TIMESTAMPTZ NOT NULL,
    end_datetime TIMESTAMPTZ,
    location TEXT NOT NULL,
    city TEXT NOT NULL,
    address TEXT,
    category TEXT NOT NULL CHECK (category IN ('music', 'tech', 'sports', 'food', 'arts', 'business', 'workshop', 'networking', 'entertainment', 'other')),
    image_url TEXT,
    capacity INTEGER,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'completed')),
    is_trending BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_datetime CHECK (datetime > created_at),
    CONSTRAINT valid_capacity CHECK (capacity IS NULL OR capacity > 0)
);

CREATE INDEX idx_events_city ON events(city);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_datetime ON events(datetime);
CREATE INDEX idx_events_organizer ON events(organizer_id);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_trending ON events(is_trending) WHERE is_trending = TRUE;

CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE rsvps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_rsvp UNIQUE(event_id, user_id)
);

CREATE INDEX idx_rsvps_event ON rsvps(event_id);
CREATE INDEX idx_rsvps_user ON rsvps(user_id);
CREATE INDEX idx_rsvps_created ON rsvps(created_at);

CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    avatar_url TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT min_name_length CHECK (length(name) >= 3)
);

CREATE INDEX idx_groups_creator ON groups(creator_id);
CREATE INDEX idx_groups_category ON groups(category);
CREATE INDEX idx_groups_public ON groups(is_public) WHERE is_public = TRUE;

CREATE TRIGGER update_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    role TEXT DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_group_member UNIQUE(group_id, user_id)
);

CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user ON group_members(user_id);
CREATE INDEX idx_group_members_role ON group_members(role);

CREATE OR REPLACE FUNCTION add_creator_as_admin()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO group_members (group_id, user_id, role)
    VALUES (NEW.id, NEW.creator_id, 'admin');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_group_created
    AFTER INSERT ON groups
    FOR EACH ROW EXECUTE FUNCTION add_creator_as_admin();

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    content TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT min_content_length CHECK (length(content) >= 1 AND length(content) <= 2000)
);
-- Indexes for fast chat history queries

CREATE INDEX idx_messages_group ON messages(group_id, created_at DESC);
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- Function: Get RSVP count for an event
CREATE OR REPLACE FUNCTION get_rsvp_count(event_uuid UUID)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER FROM rsvps WHERE event_id = event_uuid;
$$ LANGUAGE sql STABLE;

-- Function: Get member count for a group
CREATE OR REPLACE FUNCTION get_member_count(group_uuid UUID)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER FROM group_members WHERE group_id = group_uuid;
$$ LANGUAGE sql STABLE;

-- Function: Check if user has RSVP'd to event
CREATE OR REPLACE FUNCTION has_user_rsvped(event_uuid UUID, user_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS(
        SELECT 1 FROM rsvps 
        WHERE event_id = event_uuid AND user_id = user_uuid
    );
$$ LANGUAGE sql STABLE;

-- Function: Check if user is group member
CREATE OR REPLACE FUNCTION is_group_member(group_uuid UUID, user_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS(
        SELECT 1 FROM group_members 
        WHERE group_id = group_uuid AND user_id = user_uuid
    );
$$ LANGUAGE sql STABLE;

-- Function: Check if user is group admin
CREATE OR REPLACE FUNCTION is_group_admin(group_uuid UUID, user_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS(
        SELECT 1 FROM group_members 
        WHERE group_id = group_uuid AND user_id = user_uuid AND role = 'admin'
    );
$$ LANGUAGE sql STABLE;

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE rsvps ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Everyone can view profiles (public info)
CREATE POLICY "Profiles are viewable by everyone"
    ON profiles FOR SELECT
    USING (true);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Users can insert their own profile (handled by trigger mostly)
CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- Everyone can view active events
CREATE POLICY "Active events are viewable by everyone"
    ON events FOR SELECT
    USING (status = 'active' OR organizer_id = auth.uid());

-- Only organizers can create events
CREATE POLICY "Organizers can create events"
    ON events FOR INSERT
    WITH CHECK (
        auth.uid() IN (
            SELECT id FROM profiles WHERE role = 'organizer'
        )
    );

-- Only event creator can update their events
CREATE POLICY "Organizers can update own events"
    ON events FOR UPDATE
    USING (auth.uid() = organizer_id);

-- Only event creator can delete their events
CREATE POLICY "Organizers can delete own events"
    ON events FOR DELETE
    USING (auth.uid() = organizer_id);

-- Everyone can view RSVPs (to see who's attending)
CREATE POLICY "RSVPs are viewable by everyone"
    ON rsvps FOR SELECT
    USING (true);

-- Authenticated users can RSVP to events
CREATE POLICY "Authenticated users can create RSVPs"
    ON rsvps FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own RSVPs
CREATE POLICY "Users can delete own RSVPs"
    ON rsvps FOR DELETE
    USING (auth.uid() = user_id);


-- Public groups are viewable by everyone
CREATE POLICY "Public groups are viewable by everyone"
    ON groups FOR SELECT
    USING (is_public = true OR creator_id = auth.uid());

-- Authenticated users can create groups
CREATE POLICY "Authenticated users can create groups"
    ON groups FOR INSERT
    WITH CHECK (auth.uid() = creator_id);

-- Only group creator can update group
CREATE POLICY "Group creators can update own groups"
    ON groups FOR UPDATE
    USING (auth.uid() = creator_id);

-- Only group creator can delete group
CREATE POLICY "Group creators can delete own groups"
    ON groups FOR DELETE
    USING (auth.uid() = creator_id);


-- Group members can view other members
CREATE POLICY "Group members are viewable by group members"
    ON group_members FOR SELECT
    USING (
        is_group_member(group_id, auth.uid())
    );

-- Authenticated users can join groups
CREATE POLICY "Authenticated users can join groups"
    ON group_members FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can leave groups (delete their membership)
CREATE POLICY "Users can leave groups"
    ON group_members FOR DELETE
    USING (
        auth.uid() = user_id OR 
        is_group_admin(group_id, auth.uid())
    );

-- Only group members can read messages
CREATE POLICY "Group members can read messages"
    ON messages FOR SELECT
    USING (
        is_group_member(group_id, auth.uid())
    );

-- Only group members can send messages
CREATE POLICY "Group members can send messages"
    ON messages FOR INSERT
    WITH CHECK (
        auth.uid() = user_id AND
        is_group_member(group_id, auth.uid())
    );

-- Message sender or group admin can delete messages
CREATE POLICY "Sender or admin can delete messages"
    ON messages FOR UPDATE
    USING (
        auth.uid() = user_id OR 
        is_group_admin(group_id, auth.uid())
    )
    WITH CHECK (
        auth.uid() = user_id OR 
        is_group_admin(group_id, auth.uid())
    );

CREATE POLICY "Sender or admin can hard delete messages"
    ON messages FOR DELETE
    USING (
        auth.uid() = user_id OR 
        is_group_admin(group_id, auth.uid())
    );


-- View: Events with RSVP counts
CREATE OR REPLACE VIEW events_with_stats AS
SELECT 
    e.*,
    COUNT(r.id) as rsvp_count,
    p.name as organizer_name,
    p.email as organizer_email
FROM events e
LEFT JOIN rsvps r ON e.id = r.event_id
LEFT JOIN profiles p ON e.organizer_id = p.id
GROUP BY e.id, p.name, p.email;

-- View: Groups with member counts
CREATE OR REPLACE VIEW groups_with_stats AS
SELECT 
    g.*,
    COUNT(gm.id) as member_count,
    p.name as creator_name
FROM groups g
LEFT JOIN group_members gm ON g.id = gm.group_id
LEFT JOIN profiles p ON g.creator_id = p.id
GROUP BY g.id, p.name;

