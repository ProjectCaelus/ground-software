import React from "react";

const Header = ({ children }: { children: React.ReactNode }) => (
  <h1 className="text-2xl font-bold mb-2 ml-2">{children}</h1>
);

export default Header;
