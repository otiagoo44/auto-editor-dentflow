import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { create, act } from "react-test-renderer";
import { MediaPreview } from "../components/MediaPreview";
(
  globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
test("preview polling preserves playback source and refreshes expired tickets on error", async () => {
  let tree: ReturnType<typeof create>;
  await act(async () => {
    tree = create(
      React.createElement(MediaPreview, {
        identity: "a",
        url: "/first-ticket",
      }),
    );
  });
  await act(async () => {
    tree.update(
      React.createElement(MediaPreview, {
        identity: "a",
        url: "/renewed-ticket",
      }),
    );
  });
  assert.equal(tree!.root.findByType("video").props.src, "/first-ticket");
  await act(async () => {
    tree!.root.findByType("video").props.onError();
  });
  assert.equal(tree!.root.findByType("video").props.src, "/renewed-ticket");
  await act(async () => {
    tree.update(
      React.createElement(MediaPreview, {
        identity: "b",
        url: "/next-version",
      }),
    );
  });
  assert.equal(tree!.root.findByType("video").props.src, "/next-version");
  await act(async () => tree.unmount());
});
