import { DESK_SETUP_IMAGES, type Image } from "./images";
import { USERS, type User } from "./users";

export interface ImageWithUser extends Image {
  user: User;
}

export const IMAGES_WITH_USERS: ImageWithUser[] = DESK_SETUP_IMAGES.map(
  (image) => ({
    ...image,
    user: USERS.find((user) => user.id === image.user_id)!,
  }),
);
