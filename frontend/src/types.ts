export interface ImageWithUser {
  id: string;
  created_at: string;
  description: string | null;
  alt_description: string | null;
  regular_image_src: string;
  html_link: string;
  width: number;
  height: number;
  horizon_y: number;
  user: {
    name: string;
    html_link: string;
  };
}
