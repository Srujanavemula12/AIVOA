import { configureStore } from "@reduxjs/toolkit";
import interactionsReducer from "./slices/interactionsSlice";

export const store = configureStore({
  reducer: {
    interactions: interactionsReducer,
  },
});
