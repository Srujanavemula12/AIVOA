import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export const fetchInteractions = createAsyncThunk(
  "interactions/fetch",
  async (hcpId) => {
    const res = await axios.get(`${API_BASE}/interactions/`, {
      params: hcpId ? { hcp_id: hcpId } : {},
    });
    return res.data;
  }
);

export const createInteraction = createAsyncThunk(
  "interactions/create",
  async (payload) => {
    const res = await axios.post(`${API_BASE}/interactions/`, payload);
    return res.data;
  }
);

export const sendAgentMessage = createAsyncThunk(
  "interactions/agentChat",
  async ({ hcpId, message, interactionId }) => {
    const res = await axios.post(`${API_BASE}/agent/chat`, {
      hcp_id: hcpId,
      message,
      interaction_id: interactionId || null,
    });
    return res.data;
  }
);

const interactionsSlice = createSlice({
  name: "interactions",
  initialState: {
    items: [],
    chatLog: [], // { role: 'user' | 'agent', text, toolCalls? }
    activeInteraction: null, // last interaction touched via chat - drives the form sync
    status: "idle",
    error: null,
  },
  reducers: {
    appendChatMessage(state, action) {
      state.chatLog.push(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.status = "error";
        state.error = action.error.message;
      })
      .addCase(createInteraction.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
      })
      .addCase(sendAgentMessage.fulfilled, (state, action) => {
        state.chatLog.push({
          role: "agent",
          text: action.payload.reply,
          toolCalls: action.payload.tool_calls,
        });
        if (action.payload.interaction) {
          const idx = state.items.findIndex((i) => i.id === action.payload.interaction.id);
          if (idx >= 0) state.items[idx] = action.payload.interaction;
          else state.items.unshift(action.payload.interaction);
          // The form panel watches this to auto-fill from what the chat just logged.
          state.activeInteraction = action.payload.interaction;
        }
      });
  },
});

export const { appendChatMessage } = interactionsSlice.actions;
export default interactionsSlice.reducer;
