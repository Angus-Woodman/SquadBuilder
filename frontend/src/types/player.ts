export type Player = {
  player_id: number;
  name: string;
  position: string | null;
  nationality: string | null;
  date_of_birth: string | null;
  club: string | null;
  shirt_number: number | null;
  photo_url: string | null;
  england_caps: number | null;
  england_goals: number | null;
  preferred_foot: string | null;
  season_games: number | null;
  season_minutes: number | null;
  season_goals: number | null;
  season_assists: number | null;
  season_xg: string | null;
  season_xa: string | null;
  season_yellow_cards: number | null;
  season_red_cards: number | null;
  season_key_passes: number | null;
  season_shots: number | null;
};

export type PlayersResponse = {
  count: number;
  players: Player[];
};
