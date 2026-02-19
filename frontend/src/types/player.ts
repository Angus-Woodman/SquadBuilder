export type Player = {
  player_id: number;
  name: string;
  position: string | null;
  nationality: string | null;
  date_of_birth: string | null;
};

export type PlayersResponse = {
  count: number;
  players: Player[];
};
